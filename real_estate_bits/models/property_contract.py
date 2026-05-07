import calendar
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

import io
import xlsxwriter
from odoo import models
from odoo.http import request

from .project_worksite import PROJECT_WORKSITE_TYPE


def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = int(source_date.year + month / 12)
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def subtract_month(date_a, year=0, month=0):
    year, month = divmod(year * 12 + month, 12)
    if date_a.month <= month:
        year = date_a.year - year - 1
        month = date_a.month - month + 12
    else:
        year = date_a.year - year
        month = date_a.month - month
    return date_a.replace(year=year, month=month)


class Contract(models.Model):
    _name = "property.contract"
    _description = "Property Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    def _default_security_deposit_account(self):
        return self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.security_deposit_account")

    def _default_income_account(self):
        return self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.income_account")

    # rental_contract Info
    name = fields.Char("Name", size=64, default='New')
    origin = fields.Char("Source Document", size=64)

    contract_type = fields.Selection([('is_rental', 'Rental'), ('is_ownership', 'Ownership')], default='is_rental')

    type = fields.Selection(selection=PROJECT_WORKSITE_TYPE + [('shop', 'Shop')], string="Property Type")
    user_id = fields.Many2one("res.users", "Salesman", default=lambda self: self.env.user)
    partner_id = fields.Many2one("res.partner", "Tenant OR Owner", required=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)

    date = fields.Date("Date", default=fields.Date.context_today)
    date_from = fields.Date("Start Date", required=True, default=fields.Date.context_today)
    date_to = fields.Date("End Date")
    date_payment = fields.Date("First Payment Date", default=fields.Date.context_today)
    apply_tax = fields.Boolean("Apply Tax")
    tax_status = fields.Selection([("per_installment", "Per Installment"), ("tax_base_amount", "Tax Base Amount")],
                                  default="per_installment")
    attachment_line_ids = fields.One2many("attachment.line", "contract_id", "Documents")
    reservation_id = fields.Many2one("property.reservation", "Reservation")
    # commission_amount = fields.Float(string="Commission Amount", related="property.reservation.total_commission")
    # commission_base_amount = fields.Char(string="Commission Base Amount",
    #                                      related="property.reservation.commission_base_amount_selection")

    paid = fields.Float(compute="_check_amounts", string="Paid Amount")
    balance = fields.Float(compute="_check_amounts", string="Balance", )
    amount_total = fields.Float(compute="_check_amounts", string="Total Amount", )

    # Project Info
    project_id = fields.Many2one("project.worksite", related="reservation_id.project_id", store=True)

    project_code = fields.Char("Code", related="project_id.default_code", store=True)

    # Property Unit Info
    property_id = fields.Many2one("product.template", "Property", copy=False, required=True,
                                  domain=[("is_property", "=", True), ("state", "=", "free")])
    property_type_id = fields.Many2one("property.type", "Property Type", related='property_id.property_type_id',
                                       store=True)
    property_code = fields.Char("Property Code", related="property_id.default_code", store=True)
    property_area = fields.Float("Property Area", related="property_id.property_area", store=True)
    price_per_m = fields.Float("Base Price", related="property_id.price_per_m", store=True)
    floor = fields.Integer("Floor", related="property_id.floor", store=True)
    rent = fields.Integer("Rent (in month)")
    address = fields.Char("Address", related="property_id.address", store=True)

    insurance_fee = fields.Integer("Insurance fee", required=True)
    rental_fee = fields.Float("Rental fee", compute="_compute_rental_fee", digits=(25, 5), store=True)

    loan_line_ids = fields.One2many("loan.line", "contract_id")
    region_id = fields.Many2one("region.region", "Region")
    state = fields.Selection([("draft", "Draft"), ("confirmed", "Confirmed"), ("renew", "Renewed"),
                              ("cancel", "Canceled")], "Status", default=lambda *a: "draft")

    account_income = fields.Many2one("account.account", "Income Account", default=_default_income_account)
    account_security_deposit = fields.Many2one("account.account", "Security Deposit Account",
                                               default=_default_security_deposit_account)

    voucher_count = fields.Integer("Voucher Count", compute="_voucher_count")
    entry_count = fields.Integer("Entry Count", compute="_entry_count")

    periodicity = fields.Selection([("days", "Days"), ("weeks", "Weeks"), ("months", "Months"), ("years", "Years")],
                                   string="Recurrence", required=True, default="months", tracking=True,
                                   help="Invoice automatically repeat at specified interval")
    recurring_interval = fields.Integer(string="Invoicing Period", help="Repeat every (Days/Week/Month/Year)",
                                        required=True, default=1, tracking=True)

    deposit = fields.Float("Deposit")
    deposit_return_status = fields.Selection([('is_deposit_return_manually', 'Deposit Return Manually'), (
        'is_deposit_return_from_installment', 'Deposit Return From Installment')], default='is_deposit_return_manually')
    rental_agreement = fields.Selection(selection=[("per_sft", "Per SFT"), ("fixed", "Fixed Amount")],
                                        default="per_sft")

    increment_recurring_interval = fields.Integer("Increment Recurring Interval")
    increment_period = fields.Selection([("months", "Months"), ("years", "Years")],
                                        string="Increment Recurrence", required=True, default="years", tracking=True)
    increment_percentage = fields.Float("Increment Percentage")

    # Project Info
    pricing = fields.Float("Price", required=True, digits="Product Price")
    template_id = fields.Many2one("installment.template", "Installment Template")
    tax_base_amount = fields.Float("Tax Base Amount", related="property_id.tax_base_amount")
    tax_ids = fields.One2many("price.taxes", "contract_id")

    sales_price = fields.Float("Sales Price", compute="_compute_tax_and_ownership_tax")

    maintenance = fields.Float(string="Maintenance", digits="Product Price")
    date_maintenance = fields.Date("Date Maintenance")
    maintenance_type = fields.Selection([("percentage", "Percentage"), ("amount", "Amount")])

    advance_payment_method = fields.Selection([("default", "Default"), ("custom", "Custom")], default='custom')

    advance_payment_type = fields.Selection([("percentage", "Percentage"), ("amount", "Amount")], default='percentage',
                                            string="Advance Payment Type")
    advance_payment_rate = fields.Float(compute="_compute_advance_payment", string="Advance Payment %", store=True)
    advance_payment = fields.Float("Advance Payment Value", compute="_compute_advance_payment", store=True)
    advance_payment_date = fields.Date("Advance Payment Date")
    advance_payment_journal_id = fields.Many2one("account.journal", string="Advance Payment Journal")
    advance_payment_payment_id = fields.Many2one("account.payment", string="Advance Payment")

    split_contract = fields.Boolean("Split contract")

    down_payment_month0_date = fields.Date(
        string="Enganche Mensualidad 0"
    )

    contract_total_price = fields.Float(
        string="Precio Total"
    )

    contract_final_down_payment = fields.Float(
        string="Enganche Final"
    )

    contract_amount_to_finance = fields.Float(
        string="Monto a Financiar"
    )

    contract_delivery_date = fields.Date(
        string="Fecha de Entrega"
    )

    contract_financing_months = fields.Integer(
        string="Meses de Financiamiento"
    )

    @api.model_create_multi
    def create(self, vals_list):
        contracts = super(Contract, self).create(vals_list)
        for contract in contracts:
            if contract.property_type_id:
                if contract.property_type_id.name.upper() == 'NAVE' or contract.property_type_id.name.upper() == 'LOCAL COMERCIAL':
                    contract.update({
                        'split_contract': True
                    })

        return contracts


    def action_download_xlsx(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/download/sale_statement/{self.id}',
            'target': 'self',
        }

    def _generate_statement_xlsx(self):
        self.ensure_one()
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = workbook.add_worksheet("Statement")

        workbook.close()
        buffer.seek(0)
        return buffer.getvalue()

    def action_download_zip(self):
        ids_param = ','.join(str(rid) for rid in self.ids)
        return {
            'type': 'ir.actions.act_url',
            'url': f'/download/sale_statement_zip?ids={ids_param}',
            'target': 'self',
        }

    @api.depends('tax_base_amount', 'tax_ids')
    def _compute_tax_and_ownership_tax(self):
        for rec in self:
            rec.sales_price = rec.tax_base_amount + sum(rec.tax_ids.mapped("calculated_tax"))

    @api.depends("loan_line_ids.amount", "loan_line_ids.amount_residual")
    def _check_amounts(self):
        total_paid = 0
        total_non_paid = 0
        amount_total = 0
        for rec in self:
            for line in rec.loan_line_ids:
                amount_total += line.amount
                total_non_paid += line.amount_residual
                total_paid += line.amount - line.amount_residual

            rec.paid = sum(rec.loan_line_ids.filtered(lambda x: x.payment_state == 'paid').mapped('amount'))
            rec.balance = total_non_paid
            rec.amount_total = amount_total

    def get_payment_to_print(self):
        linesearch = self.env['loan.line'].search([('contract_id', '=', self.id)], order='count_line')
        all_payments = []

        for line in linesearch:
            invoice = line.invoice_id

            if invoice and invoice.state == 'posted':
                if invoice.matched_payment_ids:
                    for payment in invoice.matched_payment_ids:

                        all_payments.append({
                            'date': payment.date,
                            'amount': payment.amount,
                            'memo': payment.memo,
                        })
                else:
                    all_payments.append({
                        'date': line.payment_date,
                        'amount': line.amount_paid,
                        'memo': 'pago mensualidad',
                    })

        return all_payments



    def get_line_to_print(self):
        linesearch = self.env['loan.line'].search([
            ('contract_id', '=', self.id)
        ], order='count_line')

        linesprint = []
        for line in linesearch:
            lineadd = {
                'count_line': line.count_line,
                'date': line.date,
                'initial_balance': line.initial_balance,
                'amount': line.amount,
                'amount_capital': line.amount_capital,
                'amount_to_capital': line.amount_to_capital,
                'interest': line.interest,
                'amount_paid': line.amount_paid,
                'final_balance': line.final_balance,
                'payment_date': line.payment_date,
                'moratorium_interest': line.moratorium_interest,
                'accrued_interest': line.interest_accrued,
            }
            linesprint.append(lineadd)

        return linesprint

    def _voucher_count(self):
        voucher_obj = self.env["account.payment"]
        voucher_ids = voucher_obj.search([("real_estate_ref", "ilike", self.name)])
        self.voucher_count = len(voucher_ids)

    def _entry_count(self):
        move_obj = self.env["account.move"]
        move_ids = move_obj.search([("rental_id", "in", self.ids)])
        self.entry_count = len(move_ids)

    def auto_rental_invoice(self):
        try:
            rental_pool = self.env["loan.line"]
            rental_line_ids = rental_pool.search([("contract_id.state", "=", "confirmed"),
                                                  ("date", "<=", fields.Date.today())])
            account_move_obj = self.env["account.move"]
            journal_pool = self.env["account.journal"]
            journal = journal_pool.search([("type", "=", "sale")], limit=1)

            for line in rental_line_ids:
                if not line.invoice_id:
                    inv_dict = {
                        "journal_id": journal.id,
                        "partner_id": line.contract_id.partner_id.id,
                        "move_type": "out_invoice",
                        "rental_line_id": line.id,
                        "invoice_date_due": line.date,
                        "ref": (line.contract_id.name + " - " + line.name),
                    }

                    vals = {
                        "name": (line.contract_id.name + " - " + line.name),
                        "quantity": 1,
                        "price_unit": line.amount,
                    }

                    if line.tax_status == 'per_installment':
                        tax_ids = [(6, 0, self.env.company.account_sale_tax_id.ids,)]
                        vals.update({"tax_ids": tax_ids})

                    inv_dict["invoice_line_ids"] = [(0, None, vals)]
                    invoice = account_move_obj.create(inv_dict)
                    invoice.action_post()
                    line.invoice_id = invoice.id
        except:
            return "Internal Error"

    @api.depends("rent", "property_area", "rental_agreement")
    def _compute_rental_fee(self):
        for rec in self:
            if rec.rental_agreement == "per_sft":
                rec.rental_fee = (rec.rent or 1) * (rec.property_area or 1)
            else:
                rec.rental_fee = rec.rent

    @api.constrains("recurring_interval")
    def _check_recurring_interval(self):
        for record in self:
            if record.recurring_interval <= 0:
                raise ValidationError(_("The recurring interval must be positive"))

    # @api.constrains("date_from", "date_to")
    # def _check_dates(self):
    #     if self.filtered(lambda c: c.date_to and c.date_from > c.date_to):
    #         raise ValidationError(_("Contract start date must be less than contract end date."))

    @api.onchange("contract_type")
    def action_calculate(self):
        if self.price_per_m > 0.0 or self.rental_fee > 0.00:
            if self.contract_type == 'is_rental':
                self.prepare_lines()
            else:
                self.loan_line_ids = self._prepare_lines(self.date_payment)

    @api.onchange("region_id")
    def onchange_region(self):
        if self.region_id:
            project_ids = self.env["project.worksite"].search([("region_id", "=", self.region_id.id)])
            projects = []
            for u in project_ids:
                projects.append(u.id)
            return {"domain": {"property_id": [("id", "in", projects)]}}

    @api.onchange("project_id")
    def onchange_project(self):
        if self.project_id:
            proper_ids = self.env["product.template"].search([("is_property", "=", True),
                                                              ("project_worksite_id", "=", self.project_id.id),
                                                              ("state", "=", "free")])
            property_ids = []
            for u in proper_ids:
                property_ids.append(u.id)

            project_obj = self.env["project.worksite"].browse(self.project_id.id)
            region = project_obj.region_id.id
            owner = project_obj.partner_id.id
            if project_obj:
                return {
                    "value": {"region": region, "partner_id": owner},
                    "domain": {"property_id": [("id", "in", property_ids)]},
                }

    @api.onchange("property_id")
    def onchange_unit(self):
        self.type = self.property_id.project_type
        self.project_id = self.property_id.project_worksite_id.id
        self.region_id = self.property_id.region_id.id
        self.rental_fee = self.property_id.rental_fee
        self.insurance_fee = self.property_id.insurance_fee

    def generate_entries(self):
        journal_pool = self.env["account.journal"]
        journal = journal_pool.search([("type", "=", "sale")], limit=1)
        if not journal:
            raise UserError(_("Please set sales accounting journal!"))
        account_move_obj = self.env["account.move"]
        total = 0
        for rec in self:
            if not rec.partner_id.property_account_receivable_id:
                raise UserError(_("Please set receivable account for partner!"))
            if not rec.account_income:
                raise UserError(_("Please set income account for this contract!"))
            if rec.insurance_fee and not rec.account_security_deposit:
                raise UserError(_("Please set security deposit account for this contract!"))

            for line in rec.loan_line_ids:
                total += line.amount
            if total <= 0:
                raise UserError(_("Invalid Rental Amount!"))

            account_move_obj.create({
                "ref": rec.name, "journal_id": journal.id, "rental_id": rec.id,
                "line_ids": [
                    (0, 0, {
                        "name": rec.name,
                        "partner_id": rec.partner_id.id,
                        "account_id": rec.partner_id.property_account_receivable_id.id,
                        "debit": total,
                        "credit": 0.0}),
                    (0, 0, {
                        "name": rec.name,
                        "partner_id": rec.partner_id.id,
                        "account_id": rec.account_income.id,
                        "debit": 0.0,
                        "credit": (total - rec.insurance_fee),
                    }),
                    (0, 0, {
                        "name": rec.name,
                        "partner_id": rec.partner_id.id,
                        "account_id": rec.account_security_deposit.id,
                        "debit": 0.0,
                        "credit": rec.insurance_fee,
                    }),
                ]})

    def prepare_lines(self):
        rental_lines = []
        self.loan_line_ids = None
        for rec in self:
            if rec.periodicity and rec.date_from and rec.date_to:
                i = 1
                date_from = rec.date_from
                date_to = rec.date_to

                # if self.insurance_fee:
                #     rental_lines.append((0, 0, {
                #         "serial": i,
                #         "amount": self.insurance_fee,
                #         "date": date_from,
                #         "name": _("Insurance Deposit")
                #     }))
                #     i += 1

                rental_fee = rec.rental_fee * rec.recurring_interval
                new_date = rec.date_payment

                rental_lines.append((0, 0, {
                    "serial": i,
                    "amount": rental_fee,
                    "date": new_date,
                    "name": _("Rental Fee"),
                }))
                i += 1
                incr_new_date = rec.date_payment
                periodicity = self.periodicity
                increment_period = self.increment_period

                incr_new_date = incr_new_date + relativedelta(**{increment_period: self.increment_recurring_interval})

                while new_date < (date_to - relativedelta(**{periodicity: self.recurring_interval})):
                    new_date = new_date + relativedelta(**{periodicity: self.recurring_interval})

                    if incr_new_date <= new_date:
                        incr_new_date = incr_new_date + relativedelta(
                            **{increment_period: self.increment_recurring_interval})

                        rental_fee += (rental_fee * self.increment_percentage) / 100

                    rental_lines.append((0, 0, {
                        "serial": i,
                        "amount": rental_fee,
                        "date": new_date,
                        "name": _("Rental Fee"),
                    }))
                    i += 1
                self.write({"loan_line_ids": rental_lines})

    # Ownership Contract
    # @api.onchange("template_id", "date_payment", "pricing", "advance_payment")
    # def onchange_tmpl(self):
    #     for rec in self:
    #         if rec.template_id:
    #             if rec.contract_type == 'is_ownership':
    #                 rec.loan_line_ids = False
    #                 rec.loan_line_ids = rec._prepare_lines(rec.date_payment)
    #             else:
    #                 rec.loan_line_ids = False
    #                 rec.loan_line_ids = rec.prepare_lines()

    @api.onchange("reservation_id")
    def onchange_reservation(self):
        self.project_id = self.reservation_id.project_id.id
        self.region_id = self.reservation_id.region_id.id
        self.partner_id = self.reservation_id.partner_id.id
        self.property_id = self.reservation_id.property_id.id
        self.address = self.reservation_id.address
        self.floor = self.reservation_id.floor
        self.pricing = self.reservation_id.net_price
        self.date_payment = self.reservation_id.date_payment
        self.template_id = self.reservation_id.template_id.id
        self.type = self.reservation_id.type
        self.property_area = self.reservation_id.property_area
        self.action_update_contract_finance_values()
        # if self.template_id:
        #     self.loan_line_ids = self._prepare_lines(self.date_payment)

    def action_receive_deposit(self):
        if not self.advance_payment_journal_id:
            raise UserError(_("Please set the Advance Payment Journal!"))
        if not self.advance_payment_date:
            raise UserError(_("Please set the Advance Payment Date!"))
        # pricing = self.pricing
        # custom_adv_payment = (self.advance_payment if self.advance_payment_type == "amount"
        #                       else (pricing * (self.advance_payment / 100)))
        custom_adv_payment = self.advance_payment
        rec = self.env["account.payment"].create({
            "payment_type": "inbound",
            "partner_type": "customer",
            "amount": custom_adv_payment,
            "partner_id": self.partner_id.id,
            "date": self.advance_payment_date,
        })
        rec.action_post()
        self.advance_payment_payment_id = rec.id

    @api.depends("template_id", "advance_payment_type", "advance_payment_method")
    def _compute_advance_payment(self):
        for record in self:
            if record.advance_payment_method == 'default':
                record.advance_payment_type = "percentage"
                record.advance_payment_rate = record.template_id.adv_payment_rate
                # if record.advance_payment_type == "percentage":
                record.advance_payment = record.pricing * float(record.advance_payment_rate) / 100

            else:
                if record.advance_payment_type == "percentage":
                    record.advance_payment = record.pricing * float(record.advance_payment_rate) / 100

    @api.onchange("advance_payment_method")
    def onchange_payment(self):
        for rec in self:
            if not rec.advance_payment_method == 'default':
                rec.advance_payment = 0.00
                if rec.advance_payment_type == "percentage":
                    rec.advance_payment_rate = 0.00

    def _prepare_lines(self, date_payment):
        self.loan_line_ids = None
        loan_lines = []
        if self.template_id:
            ind = 1
            pricing = self.pricing

            mon = self.template_id.duration_month
            yr = self.template_id.duration_year
            repetition = self.template_id.repetition_rate
            deduct = self.template_id.deduct

            if not date_payment:
                raise UserError(_("Please select first payment date!"))

            if mon > 12:
                x = mon / 12
                mon = (x * 12) + mon % 12
            mons = mon + (yr * 12)

            if deduct and self.advance_payment_payment_id and self.advance_payment and self.advance_payment > 0.0:
                pricing -= self.advance_payment

            adv_payment = self.advance_payment
            if adv_payment:
                loan_lines.append((0, 0, {
                    "name": _("Advance Payment"),
                    "serial": ind,
                    "journal_id": int(
                        self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.income_journal")),
                    "amount": adv_payment,
                    "date": self.advance_payment_date,
                }))
                ind += 1
                if deduct:
                    pricing -= adv_payment

            # if self.deposit and self.deposit > 0.0:
            #     pricing -= self.deposit

            if pricing:
                loan_amount = (pricing / float(mons or 1)) * repetition
                m = 0
                while m < mons:
                    loan_lines.append((0, 0, {
                        "name": _("Loan Installment"),
                        "serial": ind,
                        "journal_id": int(
                            self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.income_journal")),
                        "amount": loan_amount,
                        "date": date_payment,
                    }))
                    ind += 1
                    date_payment = add_months(date_payment, int(repetition))
                    m += repetition
                    self.date_to = date_payment

                if self.maintenance:
                    loan_lines.append((0, 0, {
                        "name": _("Maintenance"),
                        "serial": ind,
                        "journal_id": int(
                            self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.maintenance_journal")),
                        "amount": self.maintenance
                        if self.maintenance_type == "amount"
                        else self.pricing * (self.maintenance / 100),
                        "date": self.date_maintenance,
                    }))
                    ind += 1

        return loan_lines

    def action_confirm(self):
        for contract_id in self:

            if contract_id.contract_type == 'is_rental':
                contract_id.property_id.write({"state": "on_lease"})
                contract_id.name = self.env["ir.sequence"].next_by_code("rental.contract")

            elif contract_id.contract_type == "is_ownership":
                contract_id.property_id.write({"state": "sold"})
                contract_id.name = self.env["ir.sequence"].next_by_code("ownership.contract")

        self.write({"state": "confirmed"})

    def action_cancel(self):
        for contract_obj in self:
            contract_obj.property_id.write({"state": "free"})
            contract_obj.write({"state": "cancel"})

            for line in contract_obj.loan_line_ids:
                line.invoice_id.button_draft()
                line.invoice_id.button_cancel()

    def unlink(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("You can not delete a contract not in draft state"))
            super(Contract, rec).unlink()

    def view_vouchers(self):
        vouchers = []
        voucher_obj = self.env["account.payment"]
        voucher_ids = voucher_obj.search([("real_estate_ref", "=", self.name)])
        for obj in voucher_ids:
            vouchers.append(obj.id)

        return {
            "name": _("Receipts"),
            "domain": [("id", "in", vouchers)],
            "view_type": "form",
            "view_mode": "list,form",
            "res_model": "account.payment",
            "type": "ir.actions.act_window",
            "view_id": False,
            "target": "current",
        }

    def view_entries(self):
        entries = []
        entry_obj = self.env["account.move"]
        entry_ids = entry_obj.search([("rental_id", "in", self.ids)])
        for obj in entry_ids:
            entries.append(obj.id)

        return {
            "name": _("Journal Entries"),
            "domain": [("id", "in", entries)],
            "view_type": "form",
            "view_mode": "list,form",
            "res_model": "account.move",
            "type": "ir.actions.act_window",
            "view_id": False,
            "target": "current",
        }

    def create_move(self, rec, debit, credit, move, account):
        move_line_obj = self.env["account.move.line"]
        move_line_obj.create({
            "name": rec.name,
            "partner_id": rec.partner_id.id,
            "account_id": account,
            "debit": debit,
            "credit": credit,
            "move_id": move,
        })

    def generate_cancel_entries(self):
        journal_pool = self.env["account.journal"]
        journal = journal_pool.search([("type", "=", "sale")], limit=1)
        if not journal:
            raise UserError(_("Please set sales accounting journal!"))
        account_move_obj = self.env["account.move"]
        total = 0
        for rec in self:
            if not rec.partner_id.property_account_receivable_id:
                raise UserError(_("Please set receivable account for partner!"))

            if not rec.account_income:
                raise UserError(_("Please set income account for this contract!"))

            for line in rec.loan_line_ids:
                total += line.amount

            account_move_obj.create({
                "ref": rec.name,
                "journal_id": journal.id,
                "rental_id": rec.id,
                "line_ids": [
                    (0, 0, {
                        "name": rec.name,
                        "partner_id": rec.partner_id.id,
                        "account_id": rec.partner_id.property_account_receivable_id.id,
                        "debit": 0.0,
                        "credit": total,
                    }),
                    (0, 0, {
                        "name": rec.name,
                        "partner_id": rec.partner_id.id,
                        "account_id": rec.account_income.id,
                        "debit": total,
                        "credit": 0.0,
                    }),
                ],
            })

    def send_email_notification(self):
        if self.env.company.contract_expire_reminder:
            exp_date = fields.Date + timedelta(days=self.env.company.contract_expire_reminder)
            contract_ids = self.search([('date_to', '=', exp_date)])
            template = self.env.ref('real_estate_bits.email_template_send_contract_reminder', raise_if_not_found=False)
            if template:
                for contract in contract_ids:
                    if contract and contract.id:
                        template.sudo().send_mail(contract.id, force_send=True)

    def action_update_contract_finance_values(self):
        SaleOrder = self.env["sale.order"]

        for contract in self:
            reservation = contract.reservation_id
            property_id = contract.property_id

            sale = False
            if reservation and "order_id" in reservation._fields and reservation.order_id:
                sale = reservation.order_id
            elif property_id:
                sale = SaleOrder.search([
                    ("order_line.product_template_id", "=", property_id.id),
                    ("finance_id", "!=", False),
                ], order="id desc", limit=1)

            if not sale or not sale.finance_id:
                continue

            finance_line = sale.financial_lines.filtered(
                lambda l: l.interest_id and l.interest_id.id == sale.finance_id.id
            )

            if not finance_line:
                finance_line = sale.financial_lines.filtered(
                    lambda l: l.name == sale.finance_id.name
                )

            if not finance_line:
                continue

            finance_line = finance_line[0]

            reservation_date = False
            if reservation and reservation.date:
                reservation_date = fields.Datetime.to_datetime(reservation.date).date()

            amount_total = finance_line.amount_total or 0.0
            discount_total = finance_line.discount_total or 0.0
            hitch_percent = finance_line.hitch_porcent or sale.hitch_porcent or 0.0

            amount_after_discount = amount_total - discount_total

            final_down_payment = amount_after_discount * hitch_percent
            amount_to_finance = amount_after_discount
            total_price = final_down_payment + amount_to_finance

            contract.write({
                "down_payment_month0_date": reservation_date + relativedelta(days=10) if reservation_date else False,
                "contract_total_price": total_price,
                "contract_final_down_payment": final_down_payment,
                "contract_amount_to_finance": amount_to_finance,
                "contract_delivery_date": reservation_date + relativedelta(months=property_id.month_deliver or 0) if reservation_date and property_id else False,
                "contract_financing_months": sale.finance_id.duration_month or 0,
            })