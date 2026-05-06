# -*- coding: utf-8 -*-
import pytz
import calendar
from datetime import date, timedelta
import numpy_financial as npf  # type: ignore
from dateutil.relativedelta import relativedelta

from odoo import models, _, api, fields  # type: ignore
from odoo.exceptions import UserError, ValidationError  # type: ignore
from odoo.osv.expression import FALSE_DOMAIN
from odoo.fields import Command
import sys


def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = int(source_date.year + month / 12)
    month = month % 12 + 1
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)

def _p(msg, **kw):
    extra = ""
    if kw:
        extra = " | " + " | ".join([f"{k}={v!r}" for k, v in kw.items()])
    print(f"[DBG] {msg}{extra}", flush=True)
    try:
        sys.stdout.flush()
    except Exception:
        pass


class InheritPropertyContract(models.Model):
    _inherit = 'property.contract'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency Id',
        default=lambda self: self.env.company.currency_id,
    )
    is_difered_hitch = fields.Boolean(string='Difered Hitch')
    hitch_difered_months = fields.Integer(string='Difered To:')
    periodicity_hitch = fields.Selection(
        [
            ('1', 'monthly'),
            ('2', 'Bimonthly'),
            ('3', 'Quarterly'),
            ('6', 'Biannual'),
            ('12', 'annual'),
        ],
        string='Periodicity',
        default='1',
    )
    order_id = fields.Many2one('sale.order', string='Order Id')
    moratorium_interest = fields.Float(string='Moratorium Interest')
    price_per_m = fields.Float(
        'Base Price', related='property_id.net_price', store=True
    )
    total_amount_to_pay = fields.Monetary(
        string='Total amount to pay', compute='_check_amounts'
    )
    total_interests_to_pay = fields.Monetary(
        string='Total amount of interest to pay', compute='_check_amounts'
    )
    paid = fields.Monetary(
        compute='_check_amounts', string='Paid Amount', currency_field='currency_id'
    )
    balance = fields.Monetary(
        compute='_check_amounts', string='Balance', currency_field='currency_id'
    )
    total_paid_interests = fields.Monetary(
        string='Total amount of interest to paid', compute='_check_amounts'
    )
    project_id = fields.Many2one(related='property_id.project_worksite_id')
    extra_down_payment = fields.Monetary(
        string='Extra down payment', currency_field='currency_id'
    )
    static_total_paid_interests = fields.Monetary(
        string='Property interest amount',
        compute='_compute_static_interest_amount',
        store=True,
    )


    #! ---------------------------------------------------------
    #! ACTIONS OVERRIDE
    #! ---------------------------------------------------------


    def action_receive_deposit(self):
        if not self.advance_payment_journal_id:
            raise UserError(_('Please set the Advance Payment Journal!'))
        if not self.advance_payment_date:
            raise UserError(_('Please set the Advance Payment Date!'))

        custom_adv_payment = self.advance_payment
        extra_down_payment = self.extra_down_payment

        rec = self.env['account.payment'].create(
            {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'amount': custom_adv_payment + extra_down_payment,
                'partner_id': self.partner_id.id,
                'date': self.advance_payment_date,
            }
        )
        rec.action_post()
        self.advance_payment_payment_id = rec.id

    # ---------------------------------------------------------
    # Computed Methods
    # ---------------------------------------------------------

    def _compute_static_interest_amount(self) -> None:
        for record in self:
            count_line = 0
            capital = 0
            last_capital_amounts = 0
            static_interest_value = 0
            months = record.template_id.duration_month
            adv_payment = record.advance_payment + record.extra_down_payment
            amount_to_pay = (
                record.pricing - adv_payment
                if record.template_id.deduct
                else record.pricing
            )
            for loans in record.template_id.payment_term_ids:
                loan_amounts = npf.pmt(
                    loans.interest, months, -(amount_to_pay - last_capital_amounts)
                )
                months -= loans.gap_days
                for _ in range(0, loans.gap_days):
                    count_line += 1
                    if count_line > 0:
                        amount_to_pay -= capital
                    interest = amount_to_pay * loans.interest
                    capital = loan_amounts - interest
                    last_capital_amounts = capital
                    static_interest_value += interest
            record.static_total_paid_interests = round(static_interest_value)

    @api.depends('loan_line_ids.amount', 'loan_line_ids.amount_residual')
    def _check_amounts(self) -> None:
        total_paid = 0
        total_non_paid = 0
        amount_total = 0
        total_interests = 0
        total_amount_to_paid = 0
        for rec in self:
            for line in rec.loan_line_ids:
                amount_total += line.amount_capital
                total_non_paid += line.amount_residual
                total_paid += line.amount - line.amount_residual
                total_interests += line.interest
                total_amount_to_paid += line.amount
            extra_payments_to_capital = sum(
                rec.loan_line_ids.filtered(
                    lambda x: x.capital_payment_state == 'paid'
                ).mapped('amount_to_capital')
            )
            capital_amount_paid = sum(
                rec.loan_line_ids.filtered(
                    lambda x: x.payment_state in ['paid', 'in_payment']
                ).mapped('amount_capital')
            )
            interest_amount_paid = sum(
                rec.loan_line_ids.filtered(lambda x: x.payment_state == 'paid').mapped(
                    'interest'
                )
            )
            rec.paid = (capital_amount_paid + extra_payments_to_capital)
            rec.balance = (
                (amount_total)
                - (capital_amount_paid + interest_amount_paid)
            )
            if rec.periodicity_hitch:
                rec.amount_total = sum(rec.loan_line_ids.mapped('amount_capital'))
            else:
                rec.amount_total = sum(rec.loan_line_ids.mapped('amount_capital'))

            rec.total_interests_to_pay = (total_interests)
            rec.total_amount_to_pay = (total_amount_to_paid)
            rec.total_paid_interests = (interest_amount_paid)
    def recalculate_sequence(self):
        for rec in self:
            count = 0
            try:
                loan_lines = rec.loan_line_ids.sorted(key=lambda p: p.date)
            except Exception as _:
                loan_lines = rec.loan_line_ids.sorted(key=lambda p: p.id)
            for line in loan_lines:
                count += 1
                line.count_line = count

    def _prepare_lines(self, date_payment):
        self.loan_line_ids = None

        self.loan_line_ids = None
        loan_lines = []

        hitch_amount = (self.order_id.total_hitch or 0.0) if self.order_id else 0.0
        if hitch_amount > 0.0:
            # Previous logic kept for easy rollback:
            # hitch_date = self.advance_payment_date or date_payment or fields.Date.context_today(self)
            # hitch_date = hitch_date + timedelta(days=10)
            reservation_contract_date = self.reservation_id.contract_date if self.reservation_id else False
            hitch_date = reservation_contract_date or fields.Date.context_today(self)
            hitch_date = hitch_date + timedelta(days=10)

            hitch_vals = {
                "count_line": 0,  # <- importante (muchas vistas/domains lo usan)
                "name": _("Pago enganche"),
                "serial": 0,
                "journal_id": int(
                    self.env["ir.config_parameter"].sudo().get_param("real_estate_bits.income_journal")
                ),
                "amount": hitch_amount,
                "interest": 0.0,  # <- ponlos para que no falle / no filtre
                "amount_capital": hitch_amount,
                "initial_balance": hitch_amount,
                "date": hitch_date,
            }

            loan_lines.append((0, 0, hitch_vals))

        if not self.template_id:
            return loan_lines

        ind = 1
        pricing = self.amount_finance
        mon = self.template_id.duration_month
        yr = self.template_id.duration_year
        repetition = self.template_id.repetition_rate
        deduct = self.template_id.deduct
        adv_payment = self.advance_payment + self.extra_down_payment


        if deduct:
            pricing -= adv_payment

        if not date_payment:
            raise UserError(_('Please select first payment date!'))

        if mon > 12:
            x = mon / 12
            mon_new = (x * 12) + mon % 12
            mon = mon_new

        vals = []

        pricing = self.amount_finance

        if pricing:
            count_line = 0
            amount_pay = pricing
            last_capital_amounts = 0
            months = self.template_id.duration_month


            term_idx = 0
            for loans in self.template_id.payment_term_ids:
                term_idx += 1


                base_principal = amount_pay
                loan_amounts = npf.pmt(loans.interest, months, -base_principal)

                capital = 0

                months -= loans.gap_days

                for m in range(0, loans.gap_days):
                    count_line += 1

                    initial_balance = amount_pay

                    interest = amount_pay * loans.interest
                    capital = loan_amounts - interest

                    is_last_term = (term_idx == len(self.template_id.payment_term_ids))
                    is_last_line_of_term = (m == loans.gap_days - 1)

                    if is_last_term and is_last_line_of_term:
                        capital = amount_pay
                        loan_amounts = capital + interest

                    last_capital_amounts = capital


                    vals.append({
                        'count_line': count_line,
                        'name': 'Mensualidad',
                        'serial': ind,
                        'journal_id': int(
                            self.env['ir.config_parameter']
                            .sudo()
                            .get_param('real_estate_bits.income_journal')
                        ),
                        'amount': loan_amounts,
                        'interest': interest,
                        'amount_capital': capital,
                        'initial_balance': initial_balance,
                        'date': date_payment,
                    })

                    amount_pay -= capital

                    ind += 1
                    prev_date = date_payment
                    date_payment = add_months(date_payment, int(repetition))
                    self.date_to = date_payment

            date_hitch = self.date_payment

            if self.is_difered_hitch:
                if not self.periodicity_hitch:
                    self.periodicity_hitch = '1'

                if self.hitch_difered_months <= 0:
                    raise ValidationError(_('The months for difered hitch should be greater than 0'))

                total_hitch = (self.advance_payment or 0.0) + (self.extra_down_payment or 0.0)
                difered_value = total_hitch / self.hitch_difered_months if self.hitch_difered_months else 0.0

                for i in range(0, self.hitch_difered_months):
                    date_line = list(filter(lambda x: x.get('date') == date_hitch, vals))

                    if date_line:
                        date_line[0]['difered_hitch'] = difered_value
                    else:
                        vals.append({
                            'count_line': len(vals) + 1,
                            'name': 'Enganche diferido',
                            'serial': ind,
                            'journal_id': int(
                                self.env['ir.config_parameter']
                                .sudo()
                                .get_param('real_estate_bits.income_journal')
                            ),
                            'amount': difered_value,
                            'interest': 0.0,
                            'amount_capital': 0.0,
                            'initial_balance': 0.0,
                            'difered_hitch': difered_value,
                            'date': date_hitch,
                        })
                        ind += 1

                    date_hitch = add_months(date_hitch, int(self.periodicity_hitch or '1'))


            for line in vals:
                loan_lines.append((0, 0, line))


            if self.maintenance:
                maint_amount = (
                    self.maintenance
                    if self.maintenance_type == 'amount'
                    else self.pricing * (self.maintenance / 100)
                )

                loan_lines.append((0, 0, {
                    'name': _('Maintenance'),
                    'serial': ind,
                    'journal_id': int(
                        self.env['ir.config_parameter']
                        .sudo()
                        .get_param('real_estate_bits.maintenance_journal')
                    ),
                    'amount': maint_amount,
                    'date': self.date_maintenance,
                }))
                ind += 1


        return loan_lines

    def generate_invoices(self):
        init_date = (
            fields.Datetime.now()
            .astimezone(pytz.timezone('America/Mexico_City'))
            .replace(tzinfo=None)
            .replace(day=1)
        )
        end_date = init_date + relativedelta(months=+1) + timedelta(days=-1)
        if date.today() == end_date.strftime('%Y-%m-%d'):
            invoices = self.env['loan.line'].search(
                [('date', '>=', init_date), ('date', '<=', end_date)]
            )
            invoices = invoices.filtered(lambda x: x.contract_id.state == 'confirmed')
            for invoice in invoices:
                invoice.make_invoice()

    # * ---------------------------------------------------------
    # * HELPERS
    # * ---------------------------------------------------------

    def _get_current_payment_term(
        self, current_month: int, payment_term_ids: models.Model
    ) -> models.Model:
        for payment_term in payment_term_ids:
            if int(payment_term.name) <= current_month <= int(payment_term.end_month):
                return payment_term
        return payment_term_ids[0]

    def _update_loan_line(
        self,
        line: models.Model,
        new_balance: float,
        current_payment_term: models.Model,
        is_full_payment: bool = False,
    ) -> float:
        """
        Update the line with the new balance, interest, and amount capital.

        Args:
            line (models.Model): The line to be updated.
            new_balance (float): The new balance to be applied.
            current_payment_term (models.Model): The current payment term containing interest information.
            is_full_payment (bool): Indicates if the payment is a full payment. Defaults to False.

        Returns:
            float: The remaining balance after updating the line.
        """
        amount_to_pay = new_balance
        interest = amount_to_pay * current_payment_term.interest
        line.initial_balance = new_balance

        if not is_full_payment:
            amount_capital = line.amount - interest
        else:
            amount_capital = new_balance
            line.amount = amount_capital + interest

        line.amount_capital = amount_capital
        line.interest = interest
        line.final_balance = new_balance - amount_capital

        line.final_balance_manual = (
            line.final_balance if line.final_balance_manual else 0
        )

        return new_balance - amount_capital

    def _create_payment_to_line(self, amount: float, target_line: models.Model) -> None:
        contract = target_line.contract_id
        partner = contract.partner_id

        if not partner.property_account_receivable_id:
            raise UserError(_('Please set receivable account for partner!'))
        if not contract.account_income:
            raise UserError(_('Please set income account for this contract!'))

        # Buscar un diario de ventas
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        if not journal:
            raise UserError(_('No sales journal found!'))

        # Buscar impuesto 0%
        tax_id = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
            ('name', '=', '0%')
        ], limit=1)

        # Construir línea de factura
        line_vals = {
            'product_id': self.env.ref('real_state_bits_finance_quote.product_product_capital_payment').id,
            'name': f"{contract.property_id.display_name} - {_('monthly payment number ')}{target_line.count_line}",
            'quantity': 1,
            'price_unit': amount,
            'account_id': contract.account_income.id,
            'tax_ids': [Command.set(tax_id.ids)],
        }

        # Crear diccionario de factura
        invoice_vals = {
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': fields.Date.today(),
            'ref': f"{contract.name} - monthly payment {target_line.count_line}",
            'currency_id': self.env.company.currency_id.id,
            'invoice_user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'invoice_line_ids': [(0, 0, line_vals)],
        }

        # Crear y registrar la factura
        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()

        # Relacionar factura con la línea
        target_line.capital_invoice_id = invoice.id

    def _recalculate_lines(self, start_line: int, new_balance: float) -> None:
        target_lines = sorted(
            self.loan_line_ids.filtered(lambda line: line.count_line >= start_line),  # type: ignore
            key=lambda record: record.count_line,
        )
        target_lines[0].amount_to_capital = new_balance
        self._create_payment_to_line(new_balance, target_lines[0])
        new_balance = target_lines[1].initial_balance - new_balance
        target_lines[0].final_balance = new_balance
        target_lines[0].final_balance_manual = (
            new_balance if target_lines[0].final_balance_manual else 0
        )
        payment_term_ids = self.template_id.payment_term_ids
        for line in target_lines[1:]:
            current_payment_term = self._get_current_payment_term(
                current_month=line.count_line, payment_term_ids=payment_term_ids
            )
            if new_balance >= line.amount:
                new_balance = self._update_loan_line(
                    line, new_balance, current_payment_term, is_full_payment=False
                )
            elif new_balance > 0 and line.amount > new_balance:
                new_balance = self._update_loan_line(
                    line, new_balance, current_payment_term, is_full_payment=True
                )
            else:
                line.initial_balance = 0
                line.amount = 0
                line.interest = 0
                line.amount_capital = 0
                line.final_balance = 0
                line.final_balance_manual = 0 if line.final_balance_manual else 0


    def cron_update_invoice_analytics(self):
        contracts = self.search([])
        contracts.update_invoice_analytics()

    def update_invoice_analytics(self):
        for rec in self:
            analytic_distribution = (
                    rec.property_id.worksite_id.analytic_distribution or {}
            )
            if not analytic_distribution:
                continue

            for loan_line in rec.loan_line_ids:
                invoice = loan_line.invoice_id
                if not invoice:
                    continue

                for line in invoice.invoice_line_ids:
                    line.analytic_distribution = analytic_distribution
