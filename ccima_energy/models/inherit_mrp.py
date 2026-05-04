from odoo import models, fields, api
from datetime import date

class InheritMrp(models.Model):
    _inherit = 'mrp.production'

    @api.onchange('move_raw_ids')
    def _onchange_move_raw_ids(self):
        if not self.move_raw_ids:
            return

        warehouse = False
        for line in self.move_raw_ids:
            if line.product_id:
                product_tmpl = line.product_id.product_tmpl_id
                if product_tmpl and product_tmpl.aie_warehouse_id:
                    warehouse = product_tmpl.aie_warehouse_id.lot_stock_id.id
                    line.location_id = warehouse