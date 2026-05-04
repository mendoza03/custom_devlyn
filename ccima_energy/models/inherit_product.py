from odoo import models, fields, api
from datetime import date


class InheritProduct(models.Model):
    _inherit = 'product.template'

    aie_warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
