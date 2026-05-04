import calendar
import datetime
from datetime import date, datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, AccessError
from odoo.tools.translate import _


class LoanLine(models.Model):
    _name = "loan.line"
    _description = "Loan Line"
    _order = "serial"

    name = fields.Char("Name")
    date = fields.Date("Date")
    serial = fields.Integer("#")
    amount = fields.Float("Payment", digits=(16, 4))
    paid = fields.Boolean("Paid")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)

    reservation_id = fields.Many2one("property.reservation", "", ondelete="cascade", readonly=True)
    contract_id = fields.Many2one("property.contract", "", ondelete="cascade", readonly=True)

    partner_id = fields.Many2one('res.partner', string="Partner")
    region_id = fields.Many2one('region.region', string="Region")
    project_id = fields.Many2one('project.worksite', string="Project")
    property_id = fields.Many2one('product.template', string="Property")
    user_id = fields.Many2one('res.users', string="User")

    journal_id = fields.Many2one('account.journal')
    invoice_id = fields.Many2one("account.move", string="Invoice", )
    payment_state = fields.Selection(related="invoice_id.payment_state", readonly=True)
    invoice_state = fields.Selection(related="invoice_id.state", readonly=True)
    amount_residual = fields.Monetary(related="invoice_id.amount_residual", readonly=True)
    currency_id = fields.Many2one(related="invoice_id.currency_id", readonly=True)
    tax_ids = fields.Many2many("account.tax", string="Tax")

    def make_invoice(self):
        move_obj = self.env['account.move']
        journal_pool = self.env["account.journal"]

        if not move_obj.check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                raise UserError("You have been not access to create or edit invoice")

        for rec in self:
            if not rec.contract_id.partner_id.property_account_receivable_id:
                raise UserError(_("Please set receivable account for partner!"))
            if not rec.contract_id.account_income:
                raise UserError(_("Please set income account for this contract!"))

            journal = journal_pool.search([("type", "=", "sale")], limit=1)
            inv_dict = {
                "move_type": "out_invoice",
                "journal_id": journal.id,
                "partner_id": rec.contract_id.partner_id.id,
                "line_id": rec.id,
                "invoice_date_due": rec.date,
                "ref": (rec.contract_id.name + " - " + rec.name),
                "currency_id": self.env.company.currency_id.id,
                "invoice_user_id": self.env.user.id,
                "company_id": self.env.company.id,
                "invoice_line_ids": [],
            }

            line_vals = {
                "name": (rec.contract_id.name + " - " + rec.name),
                "quantity": 1,
                "price_unit": rec.amount,
            }
            # self.tax_ids = self.env.company.account_sale_tax_id.ids
            if self.contract_id.tax_status == "tax_base_amount":
                # line_vals.update({"tax_ids": [(6, 0, self.env.company.account_sale_tax_id.ids)]})
                line_vals.update({"tax_ids": [(6, 0, rec.tax_ids.ids)]})

            elif self.contract_id.tax_status == "per_installment":
                line_vals.update({"tax_ids": [(6, 0, self.env.company.account_sale_tax_id.ids)]})

            inv_dict["invoice_line_ids"] = [
                (
                    0,
                    None,
                    line_vals
                )
            ]

            invoice = move_obj.create(inv_dict)
            self.invoice_id = invoice.id

    def view_invoice(self):
        move = (self.env["account.move"].sudo().search([("line_id", "=", self.id)]))
        return {
            "name": _("Invoice"),
            "view_type": "form",
            "res_id": move.id,
            "view_mode": "form",
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            "target": "current",
        }

    def send_multiple_installments_rent(self):
        ir_model_data = self.env["ir.model.data"]
        template_id = ir_model_data.get_object_reference(
            "real_estate_bits", "email_template_installment_notification_rent"
        )[1]
        template_res = self.env["mail.template"]
        template = template_res.browse(template_id)
        template.send_mail(self.id, force_send=True)
