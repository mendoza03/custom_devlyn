# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PropertyMap(models.Model):
    _name = "property.map"
    _description = "Property Map"

    name = fields.Char(string="Name", required=True, help="Map name")
    image = fields.Binary(string="Image", attachment=True, help="Background image for the map")
    line_ids = fields.One2many("property.map.line", "map_id", string="Lines", help="Overlay boxes")

    def action_view_map(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/property/map/{self.id}",
            "target": "new",
        }


class PropertyMapLine(models.Model):
    _name = "property.map.line"
    _description = "Property Map Line"
    _order = "id asc"

    map_id = fields.Many2one("property.map", string="Map", required=True, ondelete="cascade")

    x_pct = fields.Float(string="X (%)", digits=(16, 2), help="Left position in percentage (0..100)")
    y_pct = fields.Float(string="Y (%)", digits=(16, 2), help="Top position in percentage (0..100)")

    # NEW: configurable width / height in %
    w_pct = fields.Float(string="Width (%)", digits=(16, 2), default=20.0, help="Box width (0..100)")
    h_pct = fields.Float(string="Height (%)", digits=(16, 2), default=12.0, help="Box height (0..100)")

    product_id = fields.Many2one("product.template", string="Property", help="Product to display (name for now)")

    @api.constrains("x_pct", "y_pct", "w_pct", "h_pct")
    def _check_percent_ranges(self):
        for rec in self:
            for fname in ("x_pct", "y_pct", "w_pct", "h_pct"):
                val = getattr(rec, fname) or 0.0
                if val < 0.0 or val > 100.0:
                    raise ValidationError(f"{fname.replace('_', ' ').title()} must be between 0 and 100.")
