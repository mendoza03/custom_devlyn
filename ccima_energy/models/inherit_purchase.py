from odoo import models, fields, api
from datetime import date

class InheritPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('order_line')
    def _onchange_order_line(self):
        if not self.order_line:
            return

        warehouse = False
        for line in self.order_line:
            if line.product_id:
                product_tmpl = line.product_id.product_tmpl_id
                if product_tmpl and product_tmpl.aie_warehouse_id:
                    warehouse = product_tmpl.aie_warehouse_id.in_type_id.id
                    break
        if warehouse:
            self.picking_type_id = warehouse
