# -*- coding: utf-8 -*-

from typing import List, Dict, Union
from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, Command, _  # type: ignore
from odoo.exceptions import UserError, AccessError  # type: ignore
from odoo.addons.account.models.account_move import PAYMENT_STATE_SELECTION  # type: ignore

import logging

_logger = logging.getLogger(__name__)


class LoanLineInherit(models.Model):
    _inherit = 'loan.line'

    amount = fields.Monetary('Payment', digits=(16, 2))
    amount_residual = fields.Monetary(
        compute='_calculate_amount_residual', readonly=True, related=''
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currnency Id', related='contract_id.currency_id'
    )
    interest = fields.Monetary(string='Interest', currency_field='currency_id')
    difered_hitch = fields.Monetary(string='Amount Hitch', currency_field='currency_id')
    amount_capital = fields.Monetary(string='Capital', currency_field='currency_id')
    initial_balance = fields.Monetary(
        string='Initial Balance', currency_field='currency_id'
    )
    amount_paid = fields.Monetary(
        string='Amount Paid',
        currency_field='currency_id',
        compute='_compute_amount_paid',
    )
    amount_paid_manual = fields.Monetary(
        string='Amount paid manual', currency_field='currency_id'
    )
    count_line = fields.Integer(string='#')
    moratorium_interest = fields.Monetary(
        string='Moratorium Interest', compute='_compute_interest'
    )
    moratorium_interest_manual = fields.Float(string='Moratorium Interest Manual')
    final_balance = fields.Monetary(
        string='final balance', compute='_calculate_balance_line'
    )
    final_balance_manual = fields.Float(string='final balance manual')
    interest_of_interest = fields.Monetary(
        string='interest of interest', compute='_calculate_interest_of_interest'
    )
    interest_of_interest_manual = fields.Float(string='interest of interest manual')
    interest_accrued = fields.Monetary(
        string='interest accrued', compute='_calculate_interest_accrued'
    )
    interest_of_accrued_manual = fields.Float(string='interest of accrued manual')
    payment_state = fields.Selection(
        selection=PAYMENT_STATE_SELECTION,
        compute='_compute_payment_state',
        related=False,
        readonly=True,
    )
    payment_state_manual = fields.Selection(
        selection=PAYMENT_STATE_SELECTION, string='Manual Payment State'
    )
    payment_date = fields.Date(string='Payment Date', compute='_compute_payment_date')
    payment_date_manual = fields.Date(string='Manual Payment Date')
    capital_payment_id = fields.Many2one('account.payment', string='capital payment')
    capital_invoice_id = fields.Many2one('account.move', string='capital payment')
    amount_to_capital = fields.Monetary(
        string='Extra payments to capital', readonly=True
    )
    amount_to_capital_type = fields.Selection(
        [('positive', 'Positive'), ('normal', 'Normal'), ('negative', 'Negative')],
        string='type of capital payment',
        compute='_compute_amount_to_capital_type',
    )
    capital_payment_state = fields.Selection(
        [('paid', 'Paid'), ('normal', 'Normal'), ('draft', 'Draft'), ('debt', 'Debt')],
        string='state of capital invoice',
        compute='_compute_capital_payment_state',
    )
    show_payment_to_capital = fields.Boolean(
        string='show payment to capital', compute='_compute_show_payment_to_capital'
    )
    forgiven_interest = fields.Monetary(string='forgiven interest', readonly=True)
    credit_note_id = fields.Many2one(
        'account.move', string='credit note', compute='_compute_credit_note_id'
    )
    credit_note_type_decoration = fields.Selection(
        [
            ('draft', 'Draft'),
            ('normal', 'Normal'),
            ('positive', 'Positive'),
            ('negative', 'Negative'),
        ],
        string='credit note type decoration',
        compute='_compute_credit_note_type_decoration',
    )

    show_payment_in_current_month = fields.Boolean(string="Show Payment in Current Month", compute='_compute_show_payment_in_current_month')

    # * -------------------------------------------------------------------------
    # * COMPUTE METHODS
    # * -------------------------------------------------------------------------

    def _compute_show_payment_in_current_month(self):
        today = date.today()
        current_year = today.year
        current_month = today.month

        for record in self:
            if record.date:
                record_year = record.date.year
                record_month = record.date.month

                record.show_payment_in_current_month = (
                        record_year < current_year or
                        (record_year == current_year and record_month <= current_month)
                )
            else:
                record.show_payment_in_current_month = False

    def _compute_credit_note_type_decoration(self) -> None:
        for record in self:
            if record.credit_note_id:
                if record.credit_note_id.state == 'posted':
                    record.credit_note_type_decoration = 'positive'
                elif record.credit_note_id.state == 'cancel':
                    record.credit_note_type_decoration = 'negative'
            else:
                record.credit_note_type_decoration = 'normal'

    def _compute_credit_note_id(self) -> None:
        for record in self:
            invoice_id = record.invoice_id
            reversal_invoice = record.invoice_id.reversal_move_ids

            if invoice_id and reversal_invoice:
                record.credit_note_id = reversal_invoice[0]
                record.forgiven_interest = reversal_invoice[0].amount_total
            else:
                record.credit_note_id = False

    def _compute_show_payment_to_capital(self) -> None:
        for record in self:
            record.show_payment_to_capital = record._is_date_in_current_month()

    def _compute_amount_to_capital_type(self) -> None:
        for record in self:
            if record.amount_to_capital > 0:
                record.amount_to_capital_type = 'positive'
            elif record.amount_to_capital < 0:
                record.amount_to_capital_type = 'negative'
            else:
                record.amount_to_capital_type = 'normal'

    def _compute_capital_payment_state(self) -> None:
        for record in self:
            capital_payment_id = record.capital_payment_id
            if capital_payment_id:
                if capital_payment_id.state == 'draft':
                    record.capital_payment_state = 'draft'
                elif capital_payment_id.state in ['in_process', 'canceled', 'rejected']:
                    record.capital_payment_state = 'debt'
                elif capital_payment_id.state == 'paid':
                    record.capital_payment_state = 'paid'
            else:
                if not capital_payment_id and not record.capital_invoice_id:
                    record.update({
                        'amount_to_capital': 0.0
                    })
                record.capital_payment_state = (
                    record.payment_state_manual
                    if record.payment_state_manual == 'paid'
                    and record.amount_to_capital > 0
                    else 'normal'
                )

    @api.depends('invoice_id', 'payment_state_manual')
    def _compute_payment_state(self):
        for record in self:
            record.payment_state = (
                record.invoice_id.payment_state
                if record.invoice_id and record.invoice_id.payment_state
                else record.payment_state_manual
            )

    @api.depends('invoice_id.matched_payment_ids', 'payment_date_manual')
    def _compute_payment_date(self):
        for record in self:
            record.payment_date = (
                record.invoice_id.matched_payment_ids[0].date
                if record.invoice_id and record.invoice_id.matched_payment_ids
                else record.payment_date_manual
            )

    @api.depends('invoice_id.matched_payment_ids', 'payment_date_manual')
    def _compute_amount_paid(self) -> None:
        for rec in self:
            amount_to_capital = rec.amount_to_capital if rec.capital_invoice_id else 0
            if rec.amount_paid_manual:
                rec.amount_paid = rec.amount_paid_manual + amount_to_capital
            elif rec.invoice_id.matched_payment_ids:
                rec.amount_paid = (
                    sum(
                        payment.amount for payment in rec.invoice_id.matched_payment_ids
                    )
                    + amount_to_capital
                )
            else:
                rec.amount_paid = 0

            if rec.capital_invoice_id and rec.capital_invoice_id.payment_state == 'paid':
                capital_paid = rec.capital_invoice_id.amount_total
                rec.amount_paid += capital_paid

            if rec.amount_paid > rec.amount and not rec.capital_invoice_id:
                excess = rec.amount_paid - rec.amount
                if rec.invoice_id and rec.invoice_id.matched_payment_ids:
                    payment = rec.invoice_id.matched_payment_ids[0]
                    if payment:
                        if payment.state == 'draft':
                            rec.create_capital_invoice_from_excess(excess, rec)
                            payment.update({
                                'amount': rec.amount
                            })


    def create_capital_invoice_from_excess(self, amount: float, loan_line: models.Model) -> None:
        contract = self.contract_id
        partner = contract.partner_id

        if not partner.property_account_receivable_id:
            raise UserError(_('Please set receivable account for partner!'))
        if not contract.account_income:
            raise UserError(_('Please set income account for this contract!'))

        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        if not journal:
            raise UserError(_('No sales journal found!'))

        # Buscar impuesto 0%
        tax_id = self.env['account.tax'].search([
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
            ('name', '=', '0%')
        ], limit=1)


        line_vals = {
            'product_id': self.env.ref('real_state_bits_finance_quote.product_product_capital_payment').id,
            'name': f"{contract.property_id.display_name} - {_('monthly payment number ')}{loan_line.count_line}",
            'quantity': 1,
            'price_unit': amount,
            'account_id': contract.account_income.id,
            'tax_ids': [Command.set(tax_id.ids)],
        }

        invoice_vals = {
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': fields.Date.today(),
            'ref': f"{contract.name} - monthly payment {loan_line.count_line}",
            'currency_id': self.env.company.currency_id.id,
            'invoice_user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'invoice_line_ids': [(0, 0, line_vals)],
        }

        invoice = self.env['account.move'].create(invoice_vals)


        loan_line.capital_invoice_id = invoice.id
        loan_line.amount_to_capital = invoice.amount_total

        
    def _calculate_amount_residual(self):
        for rec in self:
            rec.amount_residual = (
                rec.invoice_id.amount_residual if not rec.payment_date_manual else 0
            )

    def _calculate_interest_accrued(self):
        for rec in self:
            accrued_interest = 0
            months_due_ids: models.Model = self._get_previous_lines_obj(rec.count_line)
            if rec.interest_of_accrued_manual:
                rec.interest_accrued = rec.interest_of_accrued_manual
                continue
            if months_due_ids and date.today() >= rec.date + relativedelta(months=1):
                accrued_interest += sum(
                    months_due_ids.mapped('moratorium_interest')
                ) + sum(months_due_ids.mapped('interest_of_interest'))

                rec.interest_accrued = (
                    rec.moratorium_interest + rec.interest_of_interest + accrued_interest
                )
            else:
                rec.interest_accrued = 0.0

    def _calculate_interest_of_interest(self):
        for rec in self:
            before_line = (
                rec.search(
                    [
                        ('count_line', '=', rec.count_line - 1),
                        ('contract_id', '=', rec.contract_id.id),
                    ],
                    limit=1,
                )
                if rec.count_line > 1
                else False
            )
            if rec.interest_of_interest_manual:
                rec.interest_of_interest = rec.interest_of_interest_manual
            elif before_line and (
                before_line.amount_residual > 0 or not before_line.invoice_id
            ):
                rec.interest_of_interest = (
                    rec.moratorium_interest
                ) * rec.contract_id.moratorium_interest
            else:
                rec.interest_of_interest = 0

    def _calculate_balance_line(self):
        for rec in self:
            if rec.final_balance_manual:
                rec.final_balance = rec.final_balance_manual
            # elif rec.amount_paid >= rec.amount_capital:
            # rec.final_balance = rec.initial_balance - rec.amount_capital
            else:
                rec.final_balance = rec.initial_balance - rec.amount_capital

    def _compute_interest(self):
        for line in self:
            line.moratorium_interest = 0
            mark_as_not_pay = line._check_invoice_status()
            if line.moratorium_interest_manual:
                if line.cal_interest_moratorium:
                    line.moratorium_interest = 0.0
                else:
                    if line.cal_interest_moratorium:
                        line.moratorium_interest = 0.0
                    else:
                        line.moratorium_interest = line.moratorium_interest_manual
            elif (
                line.date
                and not line.payment_date_manual
                and date.today() >= line.date + relativedelta(months=1)
                and mark_as_not_pay
            ):
                pay_number = line.count_line
                if pay_number > 1:
                    months_due_ids: models.Model = self._get_previous_lines_obj(
                        pay_number
                    )
                    months_due_sum = (
                        months_due_ids.sorted(
                            key=lambda line: line.count_line, reverse=True
                        )[0].interest_accrued
                        if len(months_due_ids) > 0
                        else 0
                    )
                    num_months_due = len(months_due_ids) + 1 if months_due_ids else 1
                else:
                    num_months_due = 1
                    months_due_sum = 0
                moratorium_interest_value = (
                    num_months_due * line.amount + months_due_sum
                ) * line.contract_id.moratorium_interest

                if line.cal_interest_moratorium:
                    line.moratorium_interest = 0.0
                    line.moratorium_interest_manual = 0.0
                else:
                    line.moratorium_interest = moratorium_interest_value
                    line.moratorium_interest_manual = moratorium_interest_value

    # * -------------------------------------------------------------------------
    # * ACTIONS
    # * -------------------------------------------------------------------------
    def make_payment_to_capital(self) -> Dict[str, Union[str, int]]:
        wizard_id = self.env['payment.to.capital.wizard'].create(
            {
                'contract_id': self.contract_id.id,
                'currency_id': self.currency_id.id,
                'payment_number': self.count_line,
            }
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add a payment to capital'),
            'res_model': 'payment.to.capital.wizard',
            'view_mode': 'form',
            'res_id': wizard_id.id,
            'target': 'new',
        }

    def make_invoice(self):
        move_obj = self.env['account.move']
        journal_pool = self.env['account.journal']
        if not move_obj.check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                raise UserError('You have been not access to create or edit invoice')

        for rec in self:
            if not rec.contract_id.partner_id.property_account_receivable_id:
                raise UserError(_('Please set receivable account for partner!'))
            if not rec.contract_id.account_income:
                raise UserError(_('Please set income account for this contract!'))

            journal = journal_pool.search([('type', '=', 'sale')], limit=1)
            tax_id = self.env['account.tax'].search([
                ('type_tax_use', '=', 'sale'),
                ('company_id', '=', self.env.company.id),
                ('name', '=', '0%'),
            ])

            # 🔹 Obtener la distribución analítica desde el campo correcto
            analytic_distribution = (
                    rec.contract_id.property_id.worksite_id.analytic_distribution or {}
            )

            inv_dict = {
                'move_type': 'out_invoice',
                'journal_id': journal.id,
                'partner_id': rec.contract_id.partner_id.id,
                'line_id': rec.id,
                'invoice_date_due': rec.date,
                'ref': (rec.contract_id.name + ' - ' + rec.name),
                'currency_id': self.env.company.currency_id.id,
                'invoice_user_id': self.env.user.id,
                'company_id': self.env.company.id,
                'invoice_line_ids': [],
            }

            lines_dict = []

            if rec.interest > 0:
                lines_dict.append({
                    'product_id': self.env.ref('real_state_bits_finance_quote.product_product_interest_contract').id,
                    'name': rec.contract_id.property_id.display_name + ' - ' + _('monthly payment number ') + str(
                        rec.count_line),
                    'quantity': 1,
                    'price_unit': rec.interest,
                    'tax_ids': [Command.set(tax_id.ids)],
                    'analytic_distribution': analytic_distribution,
                })

            if rec.amount_capital > 0:
                if not self.contract_id.split_contract:
                    lines_dict.append({
                        'product_id': self.env.ref('real_state_bits_finance_quote.product_product_capital_contract').id,
                        'name': rec.contract_id.property_id.display_name + ' - ' + _('monthly payment number ') + str(
                            rec.count_line),
                        'quantity': 1,
                        'price_unit': rec.amount_capital,
                        'tax_ids': [Command.set(tax_id.ids)],
                        'analytic_distribution': analytic_distribution,
                    })
                else:
                    first_pecente = rec.amount_capital * 0.8
                    second_pecente = rec.amount_capital * 0.2

                    lines_dict.append({
                        'product_id': self.env.ref(
                            'real_state_bits_finance_quote.product_product_construction_contract').id,
                        'quantity': 1,
                        'price_unit': first_pecente,
                        'tax_ids': [Command.set(tax_id.ids)],
                        'analytic_distribution': analytic_distribution,
                    })

                    lines_dict.append({
                        'product_id': self.env.ref(
                            'real_state_bits_finance_quote.product_product_property_contract').id,
                        'quantity': 1,
                        'price_unit': second_pecente,
                        'tax_ids': [Command.set(tax_id.ids)],
                        'analytic_distribution': analytic_distribution,
                    })

            if rec.difered_hitch > 0:
                lines_dict.append({
                    'product_id': self.env.ref('real_state_bits_finance_quote.product_product_difered_hitch').id,
                    'name': rec.contract_id.property_id.display_name + ' - ' + _('monthly payment number ') + str(
                        rec.count_line),
                    'quantity': 1,
                    'price_unit': rec.difered_hitch,
                    'tax_ids': [Command.set(tax_id.ids)],
                    'analytic_distribution': analytic_distribution,
                })

            if rec.moratorium_interest > 0:
                lines_dict.append({
                    'product_id': self.env.ref(
                        'real_state_bits_finance_quote.product_product_moratorium_interest_contract').id,
                    'name': rec.contract_id.property_id.display_name + ' - ' + _('monthly payment number ') + str(
                        rec.count_line),
                    'quantity': 1,
                    'price_unit': rec.moratorium_interest,
                    'tax_ids': [Command.set(tax_id.ids)],
                    'analytic_distribution': analytic_distribution,
                })

            if self.contract_id.tax_status in ('tax_base_amount', 'per_installment'):
                for val in lines_dict:
                    val.update({'tax_ids': [Command.set(tax_id.ids)]})

            if lines_dict:
                values = [(0, None, val) for val in lines_dict]
                inv_dict['invoice_line_ids'] = values

            invoice = move_obj.create(inv_dict)
            self.invoice_id = invoice.id

    #! ---------------------------------------------------------
    #! FUNCTIONS OVERRIDES
    #! ---------------------------------------------------------

    def view_invoice(self):
        return {
            'name': _('Invoice'),
            'view_type': 'form',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    # * -------------------------------------------------------------------------
    # * HELPERS
    # * -------------------------------------------------------------------------
    def _check_invoice_status(self) -> bool:
        self.ensure_one()
        if not self.invoice_id or self.payment_state != 'paid':
            return True
        else:
            return False

    def _is_date_in_current_month(self) -> bool:
        self.ensure_one()
        record_date: date = self.date
        today_date: date = fields.Date.today()
        return (
            record_date.year == today_date.year
            and record_date.month == today_date.month
        )

    def _get_previous_lines_obj(self, current_line: int) -> List[int]:
        lines_domain = list(range(1, current_line))
        loan_line_ids = self.contract_id.loan_line_ids
        previous_lines = loan_line_ids.filtered(
            lambda line: line.count_line in lines_domain
        )
        months_due_ids = previous_lines.filtered(lambda line: line.amount_residual > 0)
        return months_due_ids

    def _is_date_in_current_month(self) -> bool:
        self.ensure_one()
        record_date: date = self.date
        today_date: date = fields.Date.today()
        return (
            record_date.year == today_date.year
            and record_date.month == today_date.month
        )

    def _get_previous_lines_obj(self, current_line: int) -> List[int]:
        lines_domain = list(range(1, current_line))
        loan_line_ids = self.contract_id.loan_line_ids
        previous_lines = loan_line_ids.filtered(
            lambda line: line.count_line in lines_domain
        )
        months_due_ids = previous_lines.filtered(lambda line: line.amount_residual > 0)
        return months_due_ids
