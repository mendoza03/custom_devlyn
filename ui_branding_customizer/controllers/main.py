from odoo import http
from odoo.http import request


class UIBrandingCustomizerController(http.Controller):

    @http.route("/ui_branding_customizer/config", type="json", auth="user")
    def get_ui_branding_config(self):
        icp = request.env["ir.config_parameter"].sudo()

        def _get(key, default=""):
            return icp.get_param(key, default)

        return {
            "primary_color": _get("ui_branding_customizer.primary_color", "#5B21B6"),
            "secondary_color": _get("ui_branding_customizer.secondary_color", "#7C3AED"),
            "navbar_bg": _get("ui_branding_customizer.navbar_bg", "#111827"),
            "menu_bg": _get("ui_branding_customizer.menu_bg", "#1F2937"),
            "menu_text": _get("ui_branding_customizer.menu_text", "#F9FAFB"),
            "body_bg": _get("ui_branding_customizer.body_bg", "#F3F4F6"),
            "text_color": _get("ui_branding_customizer.text_color", "#111827"),
            "link_color": _get("ui_branding_customizer.link_color", "#2563EB"),
            "button_bg": _get("ui_branding_customizer.button_bg", "#5B21B6"),
            "button_text": _get("ui_branding_customizer.button_text", "#FFFFFF"),
            "border_radius": int(_get("ui_branding_customizer.border_radius", "10") or 10),
            "font_family": _get("ui_branding_customizer.font_family", "Inter, sans-serif"),
            "font_size": int(_get("ui_branding_customizer.font_size", "14") or 14),

            "app_menu_style": _get("ui_branding_customizer.app_menu_style", "gradient"),
            "app_menu_bg_color_1": _get("ui_branding_customizer.app_menu_bg_color_1", "#041B4D"),
            "app_menu_bg_color_2": _get("ui_branding_customizer.app_menu_bg_color_2", "#123F92"),
            "app_menu_bg_color_3": _get("ui_branding_customizer.app_menu_bg_color_3", "#19BFE6"),
            "app_menu_gradient_angle": int(_get("ui_branding_customizer.app_menu_gradient_angle", "135") or 135),
            "app_menu_overlay_opacity": int(_get("ui_branding_customizer.app_menu_overlay_opacity", "18") or 18),
            "app_menu_logo_opacity": int(_get("ui_branding_customizer.app_menu_logo_opacity", "18") or 18),
            "app_menu_shadow": int(_get("ui_branding_customizer.app_menu_shadow", "18") or 18),

            "internal_logo_width": int(_get("ui_branding_customizer.internal_logo_width", "220") or 220),
            "internal_logo_opacity": int(_get("ui_branding_customizer.internal_logo_opacity", "12") or 12),
        }