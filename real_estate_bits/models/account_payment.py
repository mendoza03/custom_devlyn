# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends('partner_type')
    def _check_partner_type(self):
        for rec in self:
            rec.sales_commission_apply = False
            if rec.partner_type == 'customer':
                rec.sales_commission_apply = True

    @api.model
    def get_team(self):
        if self._context.get('active_model') and self._context.get('active_model') == 'account.move':
            invoice = self._context.get('active_id', False)
            if invoice:
                inv = self.env['account.move'].browse(invoice)
                return inv.team_id.id
        return False

    @api.model
    def get_team_person(self):
        if self._context.get('active_model') and self._context.get('active_model') == 'account.move':
            invoice = self._context.get('active_id', False)
            if invoice:
                inv = self.env['account.move'].browse(invoice)
                return inv.user_id.id
        return False

    sales_team_id = fields.Many2one('crm.team', string='Sale Team', default=get_team)
    sales_user_id = fields.Many2one('res.users', string='Sales User', default=get_team_person)

    real_estate_ref = fields.Char("Real Estate Ref.")

    reservation_id = fields.Many2one("property.reservation", "Reservation")
    loan_line_id = fields.Many2one("loan.line", "Loan Line")

    commission_manager_id = fields.Many2one('sales.commission.line', string='Sales Commission for Manager')
    commission_person_id = fields.Many2one('sales.commission.line', string='Sales Commission for Member')
    sales_commission_apply = fields.Boolean(string='Sales Commission Apply', compute='_check_partner_type', store=True)

    # def get_team_wise_commission(self):
    #     amount_person, amount_manager = 0.0, 0.0
    #
    #     if self.reservation_id:
    #         return amount_person, amount_manager
    #
    #     for payment in self:
    #         if not self._context.get('active_ids') and not payment.sales_team_id:
    #             raise UserError(_('Please select Sales Team.'))
    #         if not self._context.get('active_ids') and not payment.sales_user_id:
    #             raise UserError(_('Please select Sales User.'))
    #         active_model = self._context.get('active_model')
    #         if self._context.get('active_ids') and not payment.sales_team_id:
    #             invoice_ids = self._context.get('active_ids')
    #             invoice_ids = self.env[active_model].sudo().browse(invoice_ids)
    #             # payment.sales_team_id = invoice_ids[0].team_id.id
    #             payment.sales_team_id = invoice_ids[0].move_id.team_id.id
    #         if self._context.get('active_ids') and not payment.sales_user_id:
    #             invoice_ids = self._context.get('active_ids')
    #             invoice_ids = self.env[active_model].sudo().browse(invoice_ids)
    #             # payment.sales_user_id = invoice_ids[0].user_id.id
    #             payment.sales_user_id = invoice_ids[0].move_id.user_id.id
    #
    #         commission_type = payment.sales_team_id.commission_type
    #         if commission_type:
    #             if payment.sales_team_id.commission_range_ids:
    #                 total = payment.amount
    #                 if payment.company_id.currency_id != payment.currency_id:
    #                     amount = payment.currency_id.compute(payment.amount, payment.company_id.currency_id)
    #                     total = amount
    #                 for range in payment.sales_team_id.commission_range_ids:
    #                     if range.starting_range <= total <= range.ending_range:
    #                         if commission_type == 'fix':
    #                             sales_manager_commission = range.sales_manager_commission_amount
    #                             sales_person_commission = range.sales_person_commission_amount
    #                         else:
    #                             sales_manager_commission = (payment.amount * range.sales_manager_commission) / 100
    #                             sales_person_commission = (payment.amount * range.sales_person_commission) / 100
    #
    #                         amount_manager = sales_manager_commission
    #                         amount_person = sales_person_commission
    #     return amount_person, amount_manager
    #
    # def create_commission(self, amount, commission, type):
    #     commission_obj = self.env['sales.commission.line']
    #     product = self.env['product.product'].search([('is_commission_product', '=', 1)], limit=1)
    #     for payment in self:
    #         if amount != 0.0:
    #             commission_value = {
    #                 'sales_team_id': payment.sales_team_id.id,
    #                 'amount': amount,
    #                 'origin': payment.name,
    #                 'type': type,
    #                 'product_id': product.id,
    #                 'date': payment.date,
    #                 'src_payment_id': payment.id,
    #                 'sales_commission_id': commission.id,
    #                 'company_id': payment.company_id.id,
    #                 'currency_id': payment.company_id.currency_id.id,
    #             }
    #             commission_id = commission_obj.create(commission_value)
    #             if type == 'sales_person':
    #                 payment.commission_person_id = commission_id.id
    #             if type == 'sales_manager':
    #                 payment.commission_manager_id = commission_id.id
    #     return True
    #
    # def create_base_commission(self, type):
    #     commission_obj = self.env['sales.commission']
    #     product = self.env['product.product'].search([('is_commission_product', '=', 1)], limit=1)
    #     for order in self:
    #         if type == 'sales_person':
    #             user = order.sales_user_id.id
    #         if type == 'sales_manager':
    #             user = order.sales_team_id.user_id.id
    #         first_day_tz, last_day_tz = commission_obj._get_utc_start_end_date()
    #
    #         commission_value = {
    #             'start_date': first_day_tz,
    #             'end_date': last_day_tz,
    #             'product_id': product.id,
    #             'commission_user_id': user,
    #             'company_id': order.company_id.id,
    #             'currency_id': order.currency_id.id,
    #         }
    #         commission_id = commission_obj.create(commission_value)
    #     return commission_id
    #
    # def action_post(self):
    #     res = super(AccountPayment, self).action_post()
    #     when_to_pay = self.env.company.when_to_pay
    #     if when_to_pay == 'invoice_payment':
    #         for payment in self:
    #             if not payment.reservation_id:
    #                 if payment.sales_commission_apply:
    #                     commission_based_on = payment.company_id.commission_based_on if payment.company_id else self.env.company.commission_based_on
    #                     amount_person, amount_manager = 0.0, 0.0
    #                     if commission_based_on == 'sales_team':
    #                         amount_person, amount_manager = payment.get_team_wise_commission()
    #                     commission = self.env['sales.commission'].search([
    #                         ('commission_user_id', '=', payment.sales_user_id.id),
    #                         ('start_date', '<', payment.date),
    #                         ('end_date', '>', payment.date),
    #                         ('state', '=', 'draft'),
    #                         ('company_id', '=', payment.company_id.id),
    #                     ], limit=1)
    #                     if not commission:
    #                         commission = payment.create_base_commission(type='sales_person')
    #                     payment.create_commission(amount_person, commission, type='sales_person')
    #
    #                     if not payment.sales_user_id.id == payment.sales_team_id.user_id.id and payment.sales_team_id.user_id:
    #                         commission = self.env['sales.commission'].search([
    #                             ('commission_user_id', '=', payment.sales_team_id.user_id.id),
    #                             ('start_date', '<', payment.date),
    #                             ('end_date', '>', payment.date),
    #                             ('state', '=', 'draft'),
    #                             ('company_id', '=', payment.company_id.id),
    #                         ], limit=1)
    #                         if not commission:
    #                             commission = payment.create_base_commission(type='sales_manager')
    #                         payment.create_commission(amount_manager, commission, type='sales_manager')
    #     return res
    #
    # def action_cancel(self):
    #     res = super(AccountPayment, self).action_cancel()
    #     for rec in self:
    #         if rec.commission_manager_id:
    #             rec.commission_manager_id.state = 'exception'
    #         if rec.commission_person_id:
    #             rec.commission_person_id.state = 'exception'
    #     return res
