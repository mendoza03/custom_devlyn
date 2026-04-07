/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

const COLOR_FIELDS = [
    "ui_primary_color",
    "ui_secondary_color",
    "ui_navbar_bg",
    "ui_menu_bg",
    "ui_menu_text",
    "ui_body_bg",
    "ui_text_color",
    "ui_link_color",
    "ui_button_bg",
    "ui_button_text",
];

const COLOR_FALLBACKS = {
    ui_primary_color: "#5B21B6",
    ui_secondary_color: "#7C3AED",
    ui_navbar_bg: "#111827",
    ui_menu_bg: "#1F2937",
    ui_menu_text: "#F9FAFB",
    ui_body_bg: "#F3F4F6",
    ui_text_color: "#111827",
    ui_link_color: "#2563EB",
    ui_button_bg: "#5B21B6",
    ui_button_text: "#FFFFFF",
};

let lastLoadedConfig = null;
let refreshThemeTimeout = null;
let previewModeActive = false;

function setCSSVariable(name, value, fallback = "") {
    document.documentElement.style.setProperty(name, value || fallback);
}

function normalizeColor(value, fallback = "#5B21B6") {
    if (!value) {
        return fallback;
    }
    const val = String(value).trim();
    if (/^#[0-9A-Fa-f]{6}$/.test(val) || /^#[0-9A-Fa-f]{3}$/.test(val)) {
        return val.toUpperCase();
    }
    return fallback;
}

function applyTheme(config) {
    if (!config) {
        return;
    }

    setCSSVariable("--ui-brand-primary", normalizeColor(config.primary_color, "#5B21B6"));
    setCSSVariable("--ui-brand-secondary", normalizeColor(config.secondary_color, "#7C3AED"));
    setCSSVariable("--ui-navbar-bg", normalizeColor(config.navbar_bg, "#111827"));
    setCSSVariable("--ui-menu-bg", normalizeColor(config.menu_bg, "#1F2937"));
    setCSSVariable("--ui-menu-text", normalizeColor(config.menu_text, "#F9FAFB"));
    setCSSVariable("--ui-body-bg", normalizeColor(config.body_bg, "#F3F4F6"));
    setCSSVariable("--ui-text-color", normalizeColor(config.text_color, "#111827"));
    setCSSVariable("--ui-link-color", normalizeColor(config.link_color, "#2563EB"));
    setCSSVariable("--ui-button-bg", normalizeColor(config.button_bg, "#5B21B6"));
    setCSSVariable("--ui-button-text", normalizeColor(config.button_text, "#FFFFFF"));
    setCSSVariable("--ui-border-radius", `${config.border_radius || 10}px`);
    setCSSVariable("--ui-font-family", config.font_family || "Inter, sans-serif");
    setCSSVariable("--ui-font-size", `${config.font_size || 14}px`);
}

async function fetchSavedTheme() {
    return await rpc("/ui_branding_customizer/config", {});
}

async function loadSavedTheme() {
    try {
        const config = await fetchSavedTheme();
        lastLoadedConfig = config;
        if (!previewModeActive) {
            applyTheme(config);
        }
    } catch (error) {
        console.warn("UI Branding Customizer: could not load config", error);
    }
}

function reapplyLastTheme() {
    if (lastLoadedConfig && !previewModeActive) {
        applyTheme(lastLoadedConfig);
    }
}

function isBrandingSettingsScreen() {
    return Boolean(document.querySelector('[name="ui_primary_color"]'));
}

function scheduleThemeRefresh() {
    if (refreshThemeTimeout) {
        clearTimeout(refreshThemeTimeout);
    }

    refreshThemeTimeout = setTimeout(async () => {
        try {
            const config = await fetchSavedTheme();
            lastLoadedConfig = config;

            if (!isBrandingSettingsScreen()) {
                previewModeActive = false;
                applyTheme(config);
            }

            convertColorInputs();
        } catch (error) {
            console.warn("UI Branding Customizer: refresh failed", error);
        }
    }, 250);
}

function getFieldValueByName(name) {
    const el = document.querySelector(`[name="${name}"]`);
    if (!el) {
        return "";
    }
    if (el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA") {
        return el.value || "";
    }
    const nested = el.querySelector("input, select, textarea");
    return nested ? nested.value || "" : "";
}

function buildPreviewConfig() {
    return {
        primary_color: getFieldValueByName("ui_primary_color"),
        secondary_color: getFieldValueByName("ui_secondary_color"),
        navbar_bg: getFieldValueByName("ui_navbar_bg"),
        menu_bg: getFieldValueByName("ui_menu_bg"),
        menu_text: getFieldValueByName("ui_menu_text"),
        body_bg: getFieldValueByName("ui_body_bg"),
        text_color: getFieldValueByName("ui_text_color"),
        link_color: getFieldValueByName("ui_link_color"),
        button_bg: getFieldValueByName("ui_button_bg"),
        button_text: getFieldValueByName("ui_button_text"),
        border_radius: parseInt(getFieldValueByName("ui_border_radius") || "10", 10),
        font_family: getFieldValueByName("ui_font_family") || "Inter, sans-serif",
        font_size: parseInt(getFieldValueByName("ui_font_size") || "14", 10),
    };
}

function updatePreviewFromSettings() {
    if (!isBrandingSettingsScreen()) {
        return;
    }
    previewModeActive = true;
    applyTheme(buildPreviewConfig());
}

function findRealTextInput(fieldName) {
    const direct = document.querySelector(`input[name="${fieldName}"]`);
    if (direct) {
        return direct;
    }

    const container = document.querySelector(`[name="${fieldName}"]`);
    if (!container) {
        return null;
    }

    if (container.tagName === "INPUT") {
        return container;
    }

    return container.querySelector('input[type="text"], input:not([type]), textarea');
}

function setNativeInputValue(input, value) {
    const descriptor = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value");
    if (descriptor && descriptor.set) {
        descriptor.set.call(input, value);
    } else {
        input.value = value;
    }
}

function triggerOdooFieldChange(input) {
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
    input.dispatchEvent(new Event("blur", { bubbles: true }));
}

function syncInputValue(input, value) {
    const normalized = normalizeColor(value, COLOR_FALLBACKS[input.name] || "#5B21B6");
    setNativeInputValue(input, normalized);
    triggerOdooFieldChange(input);
}

function createColorEnhancer(input, fallbackColor) {
    if (!input || input.dataset.uiBrandingEnhanced === "1") {
        return;
    }

    const initialColor = normalizeColor(input.value, fallbackColor);
    setNativeInputValue(input, initialColor);

    input.setAttribute("maxlength", "7");
    input.classList.add("ui-branding-hex-input");

    const wrapper = document.createElement("div");
    wrapper.className = "ui-branding-color-wrapper";

    const colorPicker = document.createElement("input");
    colorPicker.type = "color";
    colorPicker.className = "ui-branding-color-picker";
    colorPicker.value = initialColor;
    colorPicker.setAttribute("aria-label", `${input.name} color picker`);

    const preview = document.createElement("span");
    preview.className = "ui-branding-color-preview";
    preview.style.backgroundColor = initialColor;

    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(colorPicker);
    wrapper.appendChild(preview);
    wrapper.appendChild(input);

    colorPicker.addEventListener("input", () => {
        const selected = normalizeColor(colorPicker.value, fallbackColor);
        preview.style.backgroundColor = selected;
        syncInputValue(input, selected);
        updatePreviewFromSettings();
    });

    input.addEventListener("input", () => {
        const normalized = normalizeColor(input.value, fallbackColor);
        preview.style.backgroundColor = normalized;

        if (/^#[0-9A-Fa-f]{6}$/.test(input.value) || /^#[0-9A-Fa-f]{3}$/.test(input.value)) {
            colorPicker.value = normalized;
        }

        updatePreviewFromSettings();
    });

    input.addEventListener("blur", () => {
        const normalized = normalizeColor(input.value, fallbackColor);
        setNativeInputValue(input, normalized);
        colorPicker.value = normalized;
        preview.style.backgroundColor = normalized;
        triggerOdooFieldChange(input);
        updatePreviewFromSettings();
    });

    input.dataset.uiBrandingEnhanced = "1";
}

function convertColorInputs() {
    for (const fieldName of COLOR_FIELDS) {
        const input = findRealTextInput(fieldName);
        createColorEnhancer(input, COLOR_FALLBACKS[fieldName] || "#5B21B6");
    }
}

function bindLivePreview() {
    if (document.body.dataset.uiBrandingPreviewBound === "1") {
        return;
    }

    document.addEventListener("input", (ev) => {
        const target = ev.target;
        if (!target || !target.name) {
            return;
        }

        if ([...COLOR_FIELDS, "ui_border_radius", "ui_font_family", "ui_font_size"].includes(target.name)) {
            updatePreviewFromSettings();
        }
    });

    document.addEventListener("change", (ev) => {
        const target = ev.target;
        if (!target || !target.name) {
            return;
        }

        if ([...COLOR_FIELDS, "ui_border_radius", "ui_font_family", "ui_font_size"].includes(target.name)) {
            updatePreviewFromSettings();
        }
    });

    document.body.dataset.uiBrandingPreviewBound = "1";
}

function observeGlobalRerender() {
    if (window.__uiBrandingObserverStarted) {
        return;
    }
    window.__uiBrandingObserverStarted = true;

    const observer = new MutationObserver(() => {
        convertColorInputs();

        if (isBrandingSettingsScreen()) {
            updatePreviewFromSettings();
        } else {
            previewModeActive = false;
            reapplyLastTheme();
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });
}

function bindNavigationRefresh() {
    if (window.__uiBrandingNavigationBound) {
        return;
    }
    window.__uiBrandingNavigationBound = true;

    window.addEventListener("hashchange", scheduleThemeRefresh);
    window.addEventListener("popstate", scheduleThemeRefresh);

    document.addEventListener("click", () => {
        setTimeout(() => {
            scheduleThemeRefresh();
        }, 300);
    });
}

function bindSaveDetection() {
    if (window.__uiBrandingSaveBound) {
        return;
    }
    window.__uiBrandingSaveBound = true;

    document.addEventListener("click", () => {
        setTimeout(async () => {
            if (!isBrandingSettingsScreen()) {
                previewModeActive = false;
                await loadSavedTheme();
            }
        }, 1200);
    });
}

function initThemeCustomizer() {
    loadSavedTheme();
    bindLivePreview();
    observeGlobalRerender();
    bindNavigationRefresh();
    bindSaveDetection();

    const delayedInit = () => {
        convertColorInputs();

        if (isBrandingSettingsScreen()) {
            updatePreviewFromSettings();
        } else {
            previewModeActive = false;
            reapplyLastTheme();
        }
    };

    setTimeout(delayedInit, 400);
    setTimeout(delayedInit, 1000);
    setTimeout(delayedInit, 2000);
    setTimeout(delayedInit, 3500);
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initThemeCustomizer);
} else {
    initThemeCustomizer();
}