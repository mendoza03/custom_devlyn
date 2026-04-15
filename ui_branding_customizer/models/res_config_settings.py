from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ui_primary_color = fields.Char(
        string="Primary Color",
        config_parameter="ui_branding_customizer.primary_color",
        default="#5B21B6",
    )
    ui_secondary_color = fields.Char(
        string="Secondary Color",
        config_parameter="ui_branding_customizer.secondary_color",
        default="#7C3AED",
    )
    ui_navbar_bg = fields.Char(
        string="Navbar Background",
        config_parameter="ui_branding_customizer.navbar_bg",
        default="#111827",
    )
    ui_menu_bg = fields.Char(
        string="Sidebar/Menu Background",
        config_parameter="ui_branding_customizer.menu_bg",
        default="#1F2937",
    )
    ui_menu_text = fields.Char(
        string="Sidebar/Menu Text",
        config_parameter="ui_branding_customizer.menu_text",
        default="#F9FAFB",
    )
    ui_body_bg = fields.Char(
        string="Body Background",
        config_parameter="ui_branding_customizer.body_bg",
        default="#F3F4F6",
    )
    ui_text_color = fields.Char(
        string="Main Text Color",
        config_parameter="ui_branding_customizer.text_color",
        default="#111827",
    )
    ui_link_color = fields.Char(
        string="Link Color",
        config_parameter="ui_branding_customizer.link_color",
        default="#2563EB",
    )
    ui_button_bg = fields.Char(
        string="Button Background",
        config_parameter="ui_branding_customizer.button_bg",
        default="#5B21B6",
    )
    ui_button_text = fields.Char(
        string="Button Text",
        config_parameter="ui_branding_customizer.button_text",
        default="#FFFFFF",
    )
    ui_border_radius = fields.Integer(
        string="Border Radius",
        config_parameter="ui_branding_customizer.border_radius",
        default=10,
    )
    ui_font_family = fields.Selection(
        selection=[
            ("Inter, sans-serif", "Inter"),
            ("Roboto, sans-serif", "Roboto"),
            ("Arial, sans-serif", "Arial"),
            ("Tahoma, sans-serif", "Tahoma"),
            ("Verdana, sans-serif", "Verdana"),
            ("'Segoe UI', sans-serif", "Segoe UI"),
            ("'Trebuchet MS', sans-serif", "Trebuchet MS"),
            ("Georgia, serif", "Georgia"),
        ],
        string="Font Family",
        config_parameter="ui_branding_customizer.font_family",
        default="Inter, sans-serif",
    )
    ui_font_size = fields.Integer(
        string="Base Font Size",
        config_parameter="ui_branding_customizer.font_size",
        default=14,
    )

    # ===== Jazzy main menu background designer =====
    ui_app_menu_style = fields.Selection(
        selection=[
            ("gradient", "Gradient"),
            ("solid", "Solid"),
        ],
        string="Main Menu Background Style",
        config_parameter="ui_branding_customizer.app_menu_style",
        default="gradient",
    )
    ui_app_menu_bg_color_1 = fields.Char(
        string="Main Menu Color 1",
        config_parameter="ui_branding_customizer.app_menu_bg_color_1",
        default="#041B4D",
    )
    ui_app_menu_bg_color_2 = fields.Char(
        string="Main Menu Color 2",
        config_parameter="ui_branding_customizer.app_menu_bg_color_2",
        default="#123F92",
    )
    ui_app_menu_bg_color_3 = fields.Char(
        string="Main Menu Color 3",
        config_parameter="ui_branding_customizer.app_menu_bg_color_3",
        default="#19BFE6",
    )
    ui_app_menu_gradient_angle = fields.Integer(
        string="Gradient Angle",
        config_parameter="ui_branding_customizer.app_menu_gradient_angle",
        default=135,
    )
    ui_app_menu_overlay_opacity = fields.Integer(
        string="Main Menu Overlay Opacity (%)",
        config_parameter="ui_branding_customizer.app_menu_overlay_opacity",
        default=18,
    )
    ui_app_menu_logo_opacity = fields.Integer(
        string="Main Menu Logo Opacity (%)",
        config_parameter="ui_branding_customizer.app_menu_logo_opacity",
        default=18,
    )
    ui_app_menu_shadow = fields.Integer(
        string="Main Menu Card/Item Shadow Strength",
        config_parameter="ui_branding_customizer.app_menu_shadow",
        default=18,
    )

    ui_internal_logo_width = fields.Integer(
        string="Internal Watermark Width",
        config_parameter="ui_branding_customizer.internal_logo_width",
        default=220,
    )
    ui_internal_logo_opacity = fields.Integer(
        string="Internal Watermark Opacity (%)",
        config_parameter="ui_branding_customizer.internal_logo_opacity",
        default=12,
    )