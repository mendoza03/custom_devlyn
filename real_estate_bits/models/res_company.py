from odoo import models, fields, api, _
# from odoo.exceptions import Warning


class ResCompany(models.Model):
    _inherit = 'res.company'

    commission_based_on = fields.Selection([('sales_team', 'Sales Team'),
                                            ('product_category', 'Product Category'),
                                            ('product_template', 'Product')], string="Calculation Based On",
                                           default='sales_team')
    when_to_pay = fields.Selection([('invoice_validate', 'Invoice Validate'), ('invoice_payment', 'Customer Payment')],
                                   string="When To Pay", default='invoice_payment')

    emi_reminder = fields.Integer()
    contract_expire_reminder = fields.Integer()
