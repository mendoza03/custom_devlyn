from odoo import models, fields, api, _

class InheritProductTemplate(models.Model):
    _inherit = 'product.template'

    promotion_ids = fields.Many2many('promotions.property', string="Promotions")

class InheritProjectWorksite(models.Model):
    _inherit = 'project.worksite'

    promotion_ids = fields.Many2many('promotions.property', string="Promotions")

