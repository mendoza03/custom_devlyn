# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Lead(models.Model):
    _inherit = 'crm.lead'

    property_id = fields.Many2one("product.template")

    def action_create_new_booking(self):
        if self.property_id:
            self.property_id.partner_id = self.partner_id

            reservation_id = self.env["property.reservation"].create({
                "partner_id": self.partner_id.id,
                "region_id": self.property_id.region_id.id,
                "project_id": self.property_id.project_worksite_id.id,
                "property_id": self.property_id.id,
                "property_code": self.property_id.default_code,
                "floor": self.property_id.floor,
                "net_price": self.property_id.net_price,
                "address": self.property_id.address,
                "property_type_id": self.property_id.property_type_id.id,
                "property_area": self.property_id.property_area,
                "price_per_m": self.property_id.price_per_m,
                "property_price_type": self.property_id.property_price_type,
                "type": self.property_id.project_type,

            })

            return {
                "type": "ir.actions.act_window",
                "res_model": 'property.reservation',
                "view_type": "form",
                "view_mode": "form",
                "target": "current",
                "res_id": reservation_id.id
            }
