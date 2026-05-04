from odoo import models, api, fields

class InheritSaleOrder(models.Model):
    _inherit = 'sale.order'

    legal_status = fields.Char(string="Legal status")

