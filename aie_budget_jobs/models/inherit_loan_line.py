from odoo import models, fields, api
from datetime import date

class InheritLoan(models.Model):
    _inherit = 'loan.line'

    cal_interest_moratorium = fields.Boolean( string='Calculate moratorium interest')
