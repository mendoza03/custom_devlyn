from odoo import fields, api, _, models
from logging import getLogger
_log = getLogger(__name__)


class DiferHitch(models.Model):
    _name = 'difer.hitch'
    _description = 'Line for hitch difered'

    name = fields.Char(string="Name")
    hitch = fields.Float(string="Hitch %")
    amount = fields.Float(string="Amount hitch")
    months = fields.Integer(string="Months")
    period_payment = fields.Selection([('2','Bimonthly'),('3','Quarterly'),('6','Biannual')],string="Periodicity" )
    finance_id = fields.Many2one('modality.finance.line', string="Finance Line Id")
    order_id = fields.Many2one('sale.order', string="Order Id")