from logging import getLogger
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PaymentTerms(models.Model):
    _name = 'payment.terms'
    _description = 'Payment terms for installment.templates'


    name = fields.Integer(string="Start month")
    end_month = fields.Integer(string="End month")
    gap_days = fields.Integer(string="Days DIference", compute="_compute_gap_days")
    interest = fields.Float(string="Interest")
    installment_template_id = fields.Many2one('installment.template', string="Installment Template Id")

    @api.depends('name','end_month')
    def _compute_gap_days(self):
        for line in self:
            line.gap_days = 0
            if line.name and line.end_month > 0:
                if line.name > line.end_month:
                    raise UserError(_('The end month should be greater than initial month'))
                line.gap_days = line.end_month - line.name + 1