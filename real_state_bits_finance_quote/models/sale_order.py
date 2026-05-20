# -*- coding: utf-8 -*-
import numpy_financial as npf
from numpy_financial import pmt
from typing import List, Dict, Any
from logging import getLogger
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict
import math


_logger = getLogger(__name__)

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    finance_ids = fields.Many2many('installment.template', string="Finance Modality")
    hitch_porcent = fields.Float(string="% Hitch")
    extra_hitch_porcent = fields.Float(string="Extra Hitch %")
    section_date = fields.Date(string="Section Date", default=fields.Date.today() + relativedelta(days=5))
    validity_date = fields.Date(default=fields.Date.today() + relativedelta(days=10))
    financial_lines = fields.One2many('modality.finance.line', 'order_id', string="Financial Lines")
    contracts = fields.Integer(string="Reservations",  compute="_compute_contracts")
    finance_id = fields.Many2one('installment.template', string="Select Finance")
    difer_hitch = fields.Boolean(string="Defer Hitch")
    val_defer = fields.Integer(string="Defer To")
    hitch_ids = fields.One2many('difer.hitch','order_id', string="Hitch Ids")
    ebroshure_file = fields.Binary(string="Ebroshure", compute="_compute_file_broshure")
    ebroshure_filename = fields.Char(string="Ebroshure Filename")
    annual_capital_gains_yield = fields.Float(string="Annual capital gains yield percentage", default=0.105)
    annual_capital_gains_yield_years = fields.Integer(string="Projection of years", default=4)
    total_hitch = fields.Float(string="Total hitch paid")

    @api.onchange('finance_id', 'financial_lines', 'financial_lines.hitch')
    def _onchange_finance_id_set_total_hitch(self):
        for record in self:
            record.total_hitch = 0.0

            if not record.finance_id:
                continue

            line = record.financial_lines.filtered(
                lambda l: l.interest_id.id == record.finance_id.id
            )

            if not line:
                line = record.financial_lines.filtered(
                    lambda l: l.name == record.finance_id.name
                )

            if line:
                record.total_hitch = line[0].hitch or 0.0

    def _get_dynamic_finance_table(self):
        self.ensure_one()
        result = defaultdict(dict)

        for line in self.financial_lines:
            interest = line.interest_id

            if not interest or not interest.payment_term_ids:
                continue

            sorted_terms = sorted(interest.payment_term_ids, key=lambda t: t.end_month or 0)
            total_months = sorted_terms[-1].end_month
            current_deb = line.amount_finance
            prev_end_month = 0

            for term in sorted_terms:
                start_month = prev_end_month + 1
                end_month = term.end_month or 0
                duration = end_month - prev_end_month
                rate = term.interest or 0.0

                if duration <= 0:
                    continue

                key = f"{start_month} a {end_month}"

                if rate == 0.0:
                    pay_month = line.amount_finance / float(total_months)
                    nm_log = total_months
                else:
                    nm = total_months - prev_end_month
                    if nm <= 0:
                        nm = duration
                    nm_log = nm
                    denom = 1.0 - math.pow(1.0 + rate, -nm)
                    if abs(denom) < 1e-12:
                        pay_month = current_deb / float(duration)
                    else:
                        pay_month = (current_deb * rate) / denom


                result[key][line.id] = {
                    'monthly_payment': round(pay_month, 2),
                    'duration': duration,
                    'finance': line,
                    'start_month': start_month,
                    'end_month': end_month,
                    'interest': rate,
                    'amount_financed': round(pay_month, 2),
                }

                for _ in range(duration):
                    pay_interest = current_deb * rate
                    pay_rest = pay_month - pay_interest
                    if pay_rest < 0:
                        pay_rest = 0.0
                    current_deb = max(0.0, current_deb - pay_rest)

                prev_end_month = end_month

        table = dict(sorted(result.items(), key=lambda k: int(k[0].split()[0])))

        for row_key, cols in table.items():
            snapshot = {lid: cols[lid]['monthly_payment'] for lid in cols}

        if self.financial_lines and table:
            last_index = len(self.financial_lines) - 1
            last_line = self.financial_lines[last_index]

            def _parse_range(name):
                try:
                    a, b = name.split(' a ')
                    return (int(a), int(b))
                except Exception:
                    return (10 ** 9, 10 ** 9)

            ordered_keys = sorted(table.keys(), key=lambda k: _parse_range(k))

            ref_val = None
            ref_rate = 0.0
            ref_key = None
            for rk in reversed(ordered_keys):
                cell = table[rk].get(last_line.id)
                if cell and cell.get('monthly_payment') is not None:
                    ref_val = cell['monthly_payment']
                    ref_rate = cell.get('interest', 0.0)
                    ref_key = rk
                    break

            if ref_val is not None and ref_key is not None:
                filled = []
                passed_ref = False
                for rk in reversed(ordered_keys):
                    if rk == ref_key:
                        passed_ref = True
                        continue
                    if not passed_ref:
                        continue

                    row = table[rk]
                    cell = row.get(last_line.id)
                    if cell and cell.get('monthly_payment') is not None:
                        break

                    if (not cell) or (cell.get('monthly_payment') is None):
                        s, e = _parse_range(rk)
                        duration = max(0, e - s)
                        row[last_line.id] = {
                            'monthly_payment': ref_val,
                            'duration': duration,
                            'finance': last_line,
                            'start_month': s,
                            'end_month': e,
                            'interest': ref_rate,
                            'amount_financed': ref_val,
                        }
                        filled.append(rk)

        for row_key, cols in table.items():
            snapshot = {lid: cols[lid]['monthly_payment'] for lid in cols}

        return table

    def _calculate_asset_projection(self) -> List[float]:
        self.ensure_one()
        asset_projection = []
        percentage_increase = self.annual_capital_gains_yield
        annual_capital_gains_yield_years = self.annual_capital_gains_yield_years
        property_area = self.order_line.product_id.property_area 
        price_lst_m2 = self.order_line.product_id.price_per_m
        
        for iteration in range(0, annual_capital_gains_yield_years):
            price_lst_m2_year = price_lst_m2 * (1 + percentage_increase)
            asset_projection.append(price_lst_m2_year * property_area)
            price_lst_m2 = price_lst_m2_year
        return asset_projection
    
    def _compute_file_broshure(self):
        for line in self:
            line.ebroshure_file = False
            if line.order_line:
                worksite = line.order_line[0].product_template_id.worksite_id
                if worksite.attachment_line_ids:
                    line.ebroshure_file = worksite.attachment_line_ids[0].file
                    

    def _compute_contracts(self):
        for line in self:
            contract_ids = line.env['property.reservation'].search([('order_id','=', self.id)])
            if contract_ids:
                line.contracts = len(contract_ids)
            else:
                line.contracts = 0


    def action_view_properties(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Properties'),
            'res_model': 'property.reservation',
            'view_mode':'list,form',
            'domain': [('order_id','=', self.id)],
            'target':'self',
            'context':{'default_order_id': self.id}
        }
    
    def action_confirm(self):
        res = super().action_confirm()
        if not self.finance_id:
            raise ValidationError(_('You should choose a modality finance'))

        sale_amount_total = 0.0

        financial_line = self.financial_lines.filtered(
            lambda l: l.interest_id and l.interest_id.id == self.finance_id.id
        )

        if not financial_line:
            financial_line = self.financial_lines.filtered(
                lambda l: l.name == self.finance_id.name
            )

        if financial_line:
            sale_amount_total = financial_line[0].gradual_initial_investment or 0.0

        print('sale_amount_total_gradual_initial_investment', sale_amount_total)

        values = {
            'date': datetime.now(),
            'partner_id': self.partner_id.id,
            'user_id': self.user_id.id,
            'order_id': self.id,
            'property_id': self.order_line[0].product_template_id.id,
            'currency_id': self.currency_id.id,
            'price_total': sale_amount_total,
            'total_reservation': sale_amount_total,
            'project_id': self.order_line[0].product_template_id.project_worksite_id.id if self.order_line[0].product_template_id and self.order_line[0].product_template_id.project_worksite_id else False,
        }
        reservation_id = self.env['property.reservation'].create(values)
        return {
            "type": "ir.actions.act_window",
            "res_model": 'property.reservation',
            "view_type": "form",
            "view_mode": "form",
            "target": "current",
            "res_id": reservation_id.id
        }


    def _get_paymemt_lines(self, payment_ids,amount):
        if payment_ids[0].installment_template_id.duration_month == 0:
            raise ValidationError(_('Months must be greater than 0'))
        values = {
            'interest_id': payment_ids[0].installment_template_id.id
        }
        if not payment_ids:
            return values
        i = 0
        m = 0
        months = payment_ids[0].installment_template_id.duration_month
        print("FINANCE LINES start amount=", amount, "months=", months, "payment_term_ids=", payment_ids.ids)
        for payment in payment_ids:
            amount_before_payment = amount
            months_before_payment = months
            quote = npf.pmt(payment.interest,months,-amount)
            i += 1
            values['financial_line_%s'%i] = quote
            print(
                "FINANCE LINES tranche=",
                i,
                "interest=",
                payment.interest,
                "months_before=",
                months_before_payment,
                "gap_days=",
                payment.gap_days,
                "amount_before=",
                amount_before_payment,
                "quote=",
                quote,
            )
            months -= payment.gap_days
            for m in range(0, payment.gap_days):
                interest = amount * payment.interest
                capital = quote - interest
                amount -= capital
            print(
                "FINANCE LINES result tranche=",
                i,
                "financial_line_field=",
                'financial_line_%s' % i,
                "remaining_amount=",
                amount,
                "remaining_months=",
                months,
            )
        print("FINANCE LINES end values=", values)
        return values


    def calculate_financial_lines(self):
        if self.finance_ids:
            finance_lines = []
            promotion_ids = []
            if self.order_line[0].product_template_id.promotion_ids:
                promotion_ids = self.order_line[0].product_template_id.promotion_ids.ids
            for finance in self.finance_ids:
                amount = self.amount_total or 0.0

                hitch_amount = amount * self.hitch_porcent if self.hitch_porcent > 0 else 0.0
                discount_total = 0.0

                amount_finance = self._get_amount_finance_after_hitch_and_discount(
                    amount_total=amount,
                    hitch_amount=hitch_amount,
                    discount_total=discount_total,
                )

                values = {
                    'name': finance.name,
                    'finance_months': finance.duration_month,
                    'interest_id': finance.id,
                    'hitch_porcent': self.hitch_porcent,
                    'amount_total': amount,
                    'hitch': hitch_amount,
                    'hitch_no_discount': hitch_amount,
                    'discount_total': discount_total,
                    'amount_finance': amount_finance,
                    'domain_promotion_ids': [
                        (
                            6,
                            0,
                            self.order_line[0].product_template_id.promotion_ids.ids
                            if self.order_line[0].product_template_id.promotion_ids
                            else self.order_line[0].product_template_id.worksite_id.promotion_ids.ids
                            if self.order_line[0].product_template_id.worksite_id.promotion_ids
                            else []
                        )
                    ],
                }

                if finance.payment_term_ids:
                    payment_lines = self._get_paymemt_lines(finance.payment_term_ids, amount_finance)
                    values.update(payment_lines)

                finance_lines.append((0, 0, values))
            self.write({
                'financial_lines': [(5,0,0)] + finance_lines,
            })
            if not self.difer_hitch:
                self.write({
                    'total_hitch': self.amount_total * self.hitch_porcent if self.hitch_porcent > 0 else 0,
                })
                self.write({'hitch_ids': [(5,0,0)]})

    def action_calculate_difered_hitch(self):
        for order in self:
            if not order.difer_hitch:
                raise ValidationError(_('You must enable Defer Hitch first.'))
            if not order.financial_lines:
                raise ValidationError(_('You must calculate financial lines before generating deferred hitch lines.'))

            hitch_lines = order._difered_hitch(order.financial_lines.ids)
            order.write({'hitch_ids': [(5,0,0)] + hitch_lines})

    def _difered_hitch(self, finance_ids):
        hitch_ids = []

        if self.difer_hitch:
            if not self.val_defer > 0:
                raise ValidationError(_('The month to difer should be greater than 0'))

            finance_lines = self.financial_lines.filtered(lambda l: l.id in finance_ids)

            for finance_line in finance_lines:
                base_amount = (finance_line.amount_total or 0.0) - (finance_line.discount_total or 0.0)
                hitch_total = base_amount * (finance_line.hitch_porcent or self.hitch_porcent or 0.0)
                hitch_monthly_amount = hitch_total / self.val_defer

                hitch_ids.append((0, 0, {
                    'name': _('%(finance_name)s financing: Hitch to %(val_defer)s month(s)',
                            finance_name=finance_line.name,
                            val_defer=str(self.val_defer)),
                    'hitch': (finance_line.hitch_porcent or self.hitch_porcent or 0.0) / self.val_defer,
                    'amount': hitch_monthly_amount,
                    'months': self.val_defer,
                    'period_payment': '1',
                    'finance_id': finance_line.id,
                }))

        return hitch_ids

    def _get_finance_modality(self):
        return self.finance_ids
    
    def _get_finance_lines(self):
        return self.financial_lines
                
    def _get_amount_finance_after_hitch_and_discount(self, amount_total, hitch_amount, discount_total):
        amount_total = amount_total or 0.0
        hitch_amount = hitch_amount or 0.0
        discount_total = discount_total or 0.0

        return max(amount_total - hitch_amount - discount_total, 0.0)

class InheritSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_property_price_per_m(self):
        self.ensure_one()
        product = self.product_id
        product_tmpl = product.product_tmpl_id

        price_per_m = getattr(product, 'price_per_m', 0.0) or getattr(product_tmpl, 'price_per_m', 0.0)
        list_price = product.lst_price or product_tmpl.list_price or 0.0

        return price_per_m if price_per_m and price_per_m > 0 else list_price

    def _get_property_area(self):
        self.ensure_one()
        product = self.product_id
        product_tmpl = product.product_tmpl_id

        area = getattr(product, 'property_area', 0.0) or getattr(product_tmpl, 'property_area', 0.0)
        return area if area and area > 0 else 1.0

    @api.onchange('product_id')
    def _onchange_product_id_property_price(self):
        for line in self:
            if not line.product_id or line.display_type:
                continue

            line.product_uom_qty = line._get_property_area()
            line.price_unit = line._get_property_price_per_m()

    @api.depends(
        'product_id',
        'product_uom',
        'product_uom_qty',
        'product_id.lst_price',
        'product_id.product_tmpl_id.list_price',
    )
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self:
            if not line.product_id or line.display_type:
                continue

            if line.qty_invoiced > 0 or (line.product_id.expense_policy == 'cost' and line.is_expense):
                continue

            line.price_unit = line._get_property_price_per_m()

    @api.depends(
        'display_type',
        'product_id',
    )
    def _compute_product_uom_qty(self):
        for line in self:
            if line.display_type:
                line.product_uom_qty = 0.0
                continue

            if line.product_id:
                line.product_uom_qty = line._get_property_area()
            else:
                line.product_uom_qty = 1.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            if record.product_id and not record.display_type:
                if not record.price_unit:
                    record.price_unit = record._get_property_price_per_m()
                if not record.product_uom_qty or record.product_uom_qty == 1:
                    record.product_uom_qty = record._get_property_area()

            tax_0_percentage = self.env['account.tax'].with_company(record.company_id.id).search([
                ('type_tax_use', '=', 'sale'),
                ('name', '=', '0%'),
                ('company_id', '=', record.company_id.id)
            ], limit=1)

            tax_16_percentage = self.env['account.tax'].with_company(record.company_id.id).search([
                ('type_tax_use', '=', 'sale'),
                ('name', '=', '16%'),
                ('company_id', '=', record.company_id.id)
            ], limit=1)

            record.tax_id = tax_0_percentage if record.order_id else tax_16_percentage

        return records