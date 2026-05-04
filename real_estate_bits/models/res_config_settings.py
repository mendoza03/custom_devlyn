from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    penalty_percent = fields.Float("Penalty Percentage")
    penalty_account = fields.Many2one("account.account", "Late Payments Penalty Account",
                                      config_parameter="real_estate_bits.penalty_account")
    discount_account = fields.Many2one("account.account", "Discount Account",
                                       config_parameter="real_estate_bits.discount_account")
    income_account = fields.Many2one("account.account", "Income Account",
                                     config_parameter="real_estate_bits.income_account")
    expense_account = fields.Many2one("account.account", "Managerial Expenses Account",
                                      config_parameter="real_estate_bits.expense_account")
    security_deposit_account = fields.Many2one("account.account", "Security Deposit Account",
                                               config_parameter="real_estate_bits.security_deposit_account", )
    revenue_account = fields.Many2one("account.account", "Revenue Account",
                                      config_parameter="real_estate_bits.revenue_account", )

    income_journal = fields.Many2one("account.journal", "Income Journal",
                                     config_parameter="real_estate_bits.income_journal", )
    maintenance_journal = fields.Many2one("account.journal", "Maintenance Journal",
                                          config_parameter="real_estate_bits.maintenance_journal", )

    commission_based_on = fields.Selection(string="Calculation Based On", related="company_id.commission_based_on",
                                           readonly=False)
    when_to_pay = fields.Selection(string="When To Pay", related="company_id.when_to_pay", readonly=False)

    emi_reminder = fields.Integer(string="EMI Reminder", related="company_id.emi_reminder", readonly=False)
    contract_expire_reminder = fields.Integer(string="Contract Expire Reminder",
                                              related="company_id.contract_expire_reminder", readonly=False)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param("sales_commission_target_fix_percentage.when_to_pay", self.when_to_pay)
        if self.when_to_pay == 'invoice_payment':
            if self.commission_based_on == 'product_category' or self.commission_based_on == 'product_template':
                raise UserError(
                    _("Sales Commission: You can not have commission based on product or category if you have selected "
                      "when to pay is payment."))
        ICPSudo.set_param("sales_commission_target_fix_percentage.commission_based_on", self.commission_based_on)


class Config(models.TransientModel):
    _name = "gmap.config"
    _description = "Google Config"

    @api.model
    def get_key_api(self):
        return self.env["ir.config_parameter"].sudo().get_param("google_maps_api_key")
