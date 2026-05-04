from odoo import fields, models, api, _

class PromotionsProperty(models.Model):
    _name = 'promotions.property'
    _description = 'Promotions for Property or Unit'

    name = fields.Char(string="Name")
    porcent = fields.Float(string="Porcent Discount")
    active = fields.Boolean(string="Active", default=True)
    porcent_financial = fields.Float(string="Porcent Discount financial")
    porcent_bono = fields.Float(string="Discount bono")