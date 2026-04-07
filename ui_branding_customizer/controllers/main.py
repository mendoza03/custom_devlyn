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
        }