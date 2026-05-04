# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    date_state_change = fields.Datetime(
        string="State Change Date",
        help="Date when the property state changed to reserved",
        readonly=True,
        copy=False,
    )

    def write(self, vals):
        """Override write to update date_state_change when state changes"""
        # Si se está cambiando el estado
        if "state" in vals:
            new_state = vals.get("state")
            
            # Si el nuevo estado es apartado
            if new_state == "reserved":
                for record in self:
                    # Solo actualizar si no tiene fecha o si el estado está cambiando
                    if not record.date_state_change or record.state != new_state:
                        vals["date_state_change"] = fields.Datetime.now()
                        break  # Solo necesitamos agregarlo una vez al vals
        
        return super().write(vals)