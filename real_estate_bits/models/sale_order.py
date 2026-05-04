# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import datetime
from datetime import date
from dateutil.relativedelta import relativedelta


class SaleOrder(models.Model):
    _inherit = "sale.order"

    commission_manager_id = fields.Many2one('sales.commission.line', string='Sales Commission for Manager')
    commission_person_id = fields.Many2one('sales.commission.line', string='Sales Commission for Member')

    def get_category_wise_commission(self):
        sum_line_manager = []
        sum_line_person = []
        amount_person = amount_manager = 0.0
        for order in self:
            for line in order.order_line:
                commission_type = line.product_id.categ_id.commission_type
                if commission_type:
                    if line.product_id.categ_id.commission_range_ids:
                        sales_manager_commission = 0.0
                        sales_person_commission = 0.0
                        total = line.price_subtotal
                        if line.order_id.company_id.currency_id != line.order_id.currency_id:
                            amount = line.order_id.currency_id.compute(line.price_subtotal,
                                                                       line.order_id.company_id.currency_id)
                            total = amount

                        for range in line.product_id.categ_id.commission_range_ids:
                            if total >= range.starting_range and total <= range.ending_range:  # 2500 0 - 5000
                                if commission_type == 'fix':
                                    sales_manager_commission = range.sales_manager_commission_amount
                                    sales_person_commission = range.sales_person_commission_amount
                                else:
                                    sales_manager_commission = (
                                                                       line.price_subtotal * range.sales_manager_commission) / 100
                                    sales_person_commission = (
                                                                      line.price_subtotal * range.sales_person_commission) / 100
                        sum_line_manager.append(sales_manager_commission)
                        sum_line_person.append(sales_person_commission)

        amount_manager = sum(sum_line_manager)
        amount_person = sum(sum_line_person)
        return amount_person, amount_manager

    def get_product_wise_commission(self):
        sum_line_manager = []
        sum_line_person = []
        amount_person = amount_manager = 0.0
        for order in self:
            for line in order.order_line:
                commission_type = line.product_id.commission_type
                if commission_type:
                    if line.product_id.commission_range_ids:
                        sales_manager_commission = 0.0
                        sales_person_commission = 0.0
                        total = line.price_subtotal
                        if line.order_id.company_id.currency_id != line.order_id.currency_id:
                            amount = line.order_id.currency_id.compute(line.price_subtotal,
                                                                       line.order_id.company_id.currency_id)
                            total = amount

                        for range in line.product_id.commission_range_ids:
                            if total >= range.starting_range and total <= range.ending_range:  # 2500 0 - 5000
                                if commission_type == 'fix':
                                    sales_manager_commission = range.sales_manager_commission_amount
                                    sales_person_commission = range.sales_person_commission_amount
                                else:
                                    sales_manager_commission = (
                                                                       line.price_subtotal * range.sales_manager_commission) / 100
                                    sales_person_commission = (
                                                                      line.price_subtotal * range.sales_person_commission) / 100
                        sum_line_manager.append(sales_manager_commission)
                        sum_line_person.append(sales_person_commission)

        amount_manager = sum(sum_line_manager)
        amount_person = sum(sum_line_person)
        return amount_person, amount_manager

    def get_team_wise_commission(self):
        sum_line_manager = []
        sum_line_person = []
        amount_person = amount_manager = 0.0
        for order in self:

            commission_type = order.team_id.commission_type
            if commission_type:
                if order.team_id.commission_range_ids:
                    sales_manager_commission = 0.0
                    sales_person_commission = 0.0
                    total = order.amount_untaxed
                    if order.company_id.currency_id != order.currency_id:
                        amount = order.currency_id.compute(order.amount_untaxed, order.company_id.currency_id)
                        total = amount

                    for range in order.team_id.commission_range_ids:
                        if total >= range.starting_range and total <= range.ending_range:  # 2500 0 - 5000
                            if commission_type == 'fix':
                                sales_manager_commission = range.sales_manager_commission_amount
                                sales_person_commission = range.sales_person_commission_amount
                            else:
                                sales_manager_commission = (order.amount_untaxed * range.sales_manager_commission) / 100
                                sales_person_commission = (order.amount_untaxed * range.sales_person_commission) / 100

                    amount_manager = sales_manager_commission
                    amount_person = sales_person_commission
        return amount_person, amount_manager

    def create_commission(self, amount, commission, type):
        commission_obj = self.env['sales.commission.line']
        product = self.env['product.product'].search([('is_commission_product', '=', 1)], limit=1)
        for order in self:
            # Salesperson
            if amount != 0.0:
                commission_value = {
                    'amount': amount,
                    'origin': order.name,
                    'type': type,
                    'product_id': product.id,
                    'date': order.date_order,
                    'src_order_id': order.id,
                    'sales_commission_id': commission.id,
                    'sales_team_id': order.team_id and order.team_id.id or False,
                    'company_id': order.company_id.id,
                    'currency_id': order.company_id.currency_id.id,
                }
                commission_id = commission_obj.create(commission_value)
                if type == 'sales_person':
                    order.commission_person_id = commission_id.id
                if type == 'sales_manager':
                    order.commission_manager_id = commission_id.id
        return True

    def create_base_commission(self, type):
        commission_obj = self.env['sales.commission']
        product = self.env['product.product'].search([('is_commission_product', '=', 1)], limit=1)
        for order in self:
            if type == 'sales_person':
                user = order.user_id.id
            if type == 'sales_manager':
                user = order.team_id.user_id.id

            first_day_tz, last_day_tz = self.env['sales.commission']._get_utc_start_end_date()
            commission_value = {
                'start_date': first_day_tz,
                'end_date': last_day_tz,
                'product_id': product.id,
                'commission_user_id': user,
                'company_id': order.company_id.id,
                'currency_id': order.currency_id.id,
            }
            commission_id = commission_obj.create(commission_value)
        return commission_id

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        when_to_pay = self.env.company.when_to_pay
        if when_to_pay == 'sales_confirm':
            for order in self:
                commission_based_on = order.company_id.commission_based_on if order.company_id else self.env.company.commission_based_on
                if commission_based_on == 'sales_team':
                    amount_person, amount_manager = order.get_teamwise_commission()
                elif commission_based_on == 'product_category':
                    amount_person, amount_manager = order.get_categorywise_commission()
                elif commission_based_on == 'product_template':
                    amount_person, amount_manager = order.get_productwise_commission()

                # Sale Person
                commission = self.env['sales.commission'].search([
                    ('commission_user_id', '=', order.user_id.id),
                    ('start_date', '<', order.date_order),
                    ('end_date', '>', order.date_order),
                    ('state', '=', 'draft'),
                    ('company_id', '=', order.company_id.id),
                ], limit=1)
                if not commission:
                    commission = order.create_base_commission(type='sales_person')
                order.create_commission(amount_person, commission, type='sales_person')

                # Sale Manager
                if not order.user_id.id == order.team_id.user_id.id and order.team_id.user_id:
                    commission = self.env['sales.commission'].search([
                        ('commission_user_id', '=', order.team_id.user_id.id),
                        ('start_date', '<', order.date_order),
                        ('end_date', '>', order.date_order),
                        ('state', '=', 'draft'),
                        ('company_id', '=', order.company_id.id),
                    ], limit=1)
                    if not commission:
                        commission = order.create_base_commission(type='sales_manager')
                    order.create_commission(amount_manager, commission, type='sales_manager')
        return res

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        for rec in self:
            if rec.commission_manager_id:
                rec.commission_manager_id.state = 'exception'
            if rec.commission_person_id:
                rec.commission_person_id.state = 'exception'
        return res
