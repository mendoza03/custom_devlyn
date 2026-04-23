/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { NavBar } from "@web/webclient/navbar/navbar";
import { onMounted } from "@odoo/owl";

patch(NavBar.prototype, {
    setup() {
        super.setup();

        onMounted(() => {
            const isBackendHome = () => {
                const { pathname, hash, search } = window.location;
                const normalizedPath = pathname.replace(/\/+$/, "") || "/";
                const isRootBackend = normalizedPath === "/odoo" || normalizedPath === "/web";
                if (!isRootBackend) {
                    return false;
                }
                const routeState = new URLSearchParams((hash || "").replace(/^#/, ""));
                return !(
                    routeState.get("action")
                    || routeState.get("model")
                    || routeState.get("id")
                    || routeState.get("resId")
                    || routeState.get("view_type")
                    || routeState.get("menu_id")
                    || (search && search.length > 1)
                );
            };

            const tryOpen = () => {
                try {
                    if (!isBackendHome()) {
                        return;
                    }
                    if (typeof this.OnClickMainMenu === "function") {
                        const el = this.app_components?.el;
                        const isOpen = el && el.style && el.style.display === "block";
                        if (!isOpen) {
                            this.OnClickMainMenu();
                        }
                    }
                } catch (e) {
                    console.warn("jazzy_backend_theme_home: auto-open apps failed", e);
                }
            };

            tryOpen();
            setTimeout(tryOpen, 300);
        });
    },
});
