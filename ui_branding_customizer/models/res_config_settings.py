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