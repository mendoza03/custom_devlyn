
from odoo import fields, models


class InstallmentTemplate(models.Model):
    _name = "installment.template"
    _description = "Installment Template"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char("Name", size=64, required=True)
    duration_month = fields.Integer("Month")
    duration_year = fields.Integer("Year")
    annual_raise = fields.Float("Annual Raise %")
    repetition_rate = fields.Float("Repetition Rate (month)", default=1)
    adv_payment_rate = fields.Float("Advance Payment %")
    deduct = fields.Boolean("Deducted from amount?", default=True)
    note = fields.Html("Note")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
