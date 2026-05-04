from odoo import models, fields, api
from odoo.exceptions import UserError
import math
from collections import defaultdict

class AmortizationCalculator(models.Model):
    _name = 'amortization.calculator'
    _description = 'Amortization Calculator'

    name = fields.Char(string="Name")
    partner_id = fields.Many2one('res.partner', string='Partner')
    meters = fields.Float(string="Meters")
    price_meter = fields.Float(string="Price per meter")
    price_lot = fields.Float(string="Lot price without discount", compute='_compute_values', store=True)
    discount_value = fields.Float(string="Discount", compute='_compute_values', store=True)
    initial_investment = fields.Float(string="Initial investment", compute='_compute_values', store=True)
    gradual_initial_investment = fields.Float(string="Gradual Initial Investment", compute='_compute_values', store=True)
    hitch_amount = fields.Float(string="Hitch", compute='_compute_values', store=True)
    hitch_no_discount = fields.Float(string="Hitch", compute='_compute_values', store=True)
    financing_amount = fields.Float(string="Amount to finance", compute='_compute_values', store=True)
    unit_price_discount = fields.Float(string="P.U. with discount", compute='_compute_values', store=True)
    payments = fields.Many2many('installment.template', string='Payment plans')
    comparison_line_ids = fields.One2many('amortization.comparison.line', 'amortization_id', string='Financial Comparative')
    val_year_1 = fields.Float(string="Value in 1 year")
    val_year_2 = fields.Float(string="Value in 2 year")
    val_year_3 = fields.Float(string="Value in 3 year")
    val_year_4 = fields.Float(string="Value in 4 year")
    val_year_extra = fields.Float(string="Value extra")

    promotion_id = fields.Many2one('promotions.property', string="Promotion")
    hitch_percentage = fields.Float(string="Down payment percentage", default=10.0)

    def _prepare_blocks_for_report(self):
        self.ensure_one()
        lines = self.comparison_line_ids
        all_blocks = sum((ln.comparison_block_ids for ln in lines),
                         self.env['amortization.comparison.block'])

        def _parse_range(name):
            try:
                parts = name.split()
                start = int(parts[1])
                end = int(parts[3])
                return (start, end)
            except Exception:
                return (10 ** 9, 10 ** 9)

        unique_block_names = sorted(set(all_blocks.mapped('block_name')), key=_parse_range)

        rows = []
        for bname in unique_block_names:
            row_vals = []
            for ln in lines:
                blk = ln.comparison_block_ids.filtered(lambda b: b.block_name == bname)
                amount = blk[0].amount if blk else None
                row_vals.append(amount)
            rows.append({'name': bname, 'values': row_vals})

        if rows and lines:
            last_col = len(lines) - 1

            ref = None
            for r in reversed(rows):
                v = r['values'][last_col]
                if v is not None:
                    ref = v
                    break

            if ref is not None:
                filled = []
                for r in reversed(rows):
                    if r['values'][last_col] is None:
                        r['values'][last_col] = ref
                        filled.append(r['name'])
                    else:
                        ref = r['values'][last_col]

        return rows

    def action_print_financial_year(self):
        self.ensure_one()
        if not self.exists():
            raise UserError(_("This amortization calculation no longer exists."))
        ctx = dict(self.env.context,
                   allowed_company_ids=self.env.user.company_ids.ids,
                   download=False)
        return self.env.ref('amortization_calculator.action_report_amortization_calculator')\
                 .with_context(ctx).report_action(self)

    @api.depends('meters', 'price_meter', 'hitch_percentage')
    def _compute_values(self):
        for rec in self:
            rec.price_lot = rec.meters * rec.price_meter
            rec.initial_investment = rec.meters * rec.price_meter

            promo_discount = 0.0

            rec.discount_value = promo_discount
            rec.gradual_initial_investment = rec.meters * rec.price_meter

            hitch_percent = rec.hitch_percentage / 100
            rec.hitch_amount = rec.gradual_initial_investment * hitch_percent
            rec.financing_amount = rec.meters * rec.price_meter

            rec.unit_price_discount = promo_discount

    @api.onchange('hitch_percentage')
    def _onchange_hitch_percentage(self):
        if self.hitch_percentage > 100:
            raise UserError("El porcentaje de enganche no puede ser mayor a 100%.")

    def action_generate_comparison(self):
        self.ensure_one()
        if not self.payments:
            raise UserError('Debe seleccionar al menos un plan de pago.')
        self.comparison_line_ids.unlink()
        for plan in self.payments:
            months = plan.duration_month
            cat = plan.cat

            if months <= 0:
                continue

            gradual_initial = self.gradual_initial_investment
            hitch_amount = (self.hitch_percentage / 100) * self.initial_investment
            gradual_financing = self.financing_amount

            total_r = 0.105
            year_1 = (gradual_initial * total_r) + gradual_initial
            year_2 = (year_1 * total_r) + year_1
            year_3 = (year_2 * total_r) + year_2
            year_4 = (year_3 * total_r) + year_3
            year_e = (year_3 * total_r) + year_3

            comparison = self.env['amortization.comparison.line'].create({
                'amortization_id': self.id,
                'plan_name': plan.name,
                'months': months,
                'unit_price_discount': self.price_meter,
                'price_lot': self.price_lot,
                'initial_investment': self.initial_investment,
                'gradual_initial_investment': gradual_initial,
                'hitch_amount': hitch_amount,
                'gradual_financing_amount': gradual_financing - hitch_amount,
                'financing_amount': self.financing_amount,
            })

            current_deb = gradual_financing - hitch_amount

            sorted_terms = sorted(plan.payment_term_ids, key=lambda t: t.end_month or 0)
            total_months = sorted_terms[-1].end_month if sorted_terms else 0

            prev_end_month = 0

            for term in sorted_terms:
                start_month = prev_end_month + 1
                end_month = term.end_month or 0
                duration = end_month - prev_end_month
                rate = term.interest or 0.0

                if duration <= 0:
                    continue


                if rate == 0.0:
                    pay_month = current_deb / float(total_months)
                else:
                    month_rem = total_months - prev_end_month
                    if month_rem <= 0:
                        month_rem = duration
                    denom = 1.0 - math.pow(1.0 + rate, -month_rem)
                    if abs(denom) < 1e-12:
                        pay_month = current_deb / float(duration)
                    else:
                        pay_month = (current_deb * rate) / denom

                temp_debt = current_deb
                for i in range(duration):
                    interest = temp_debt * rate
                    capital = pay_month - interest
                    capital = max(0.0, capital)
                    temp_debt = max(0.0, temp_debt - capital)

                current_deb = temp_debt

                self.env['amortization.comparison.block'].create({
                    'comparison_line_id': comparison.id,
                    'block_name': f'Mensualidad {term.name} a {end_month}',
                    'amount': pay_month,
                })


                prev_end_month = end_month

            self.update({
                'val_year_1': year_1,
                'val_year_2': year_2,
                'val_year_3': year_3,
                'val_year_4': year_4,
                'val_year_extra': year_e,
            })


class AmortizationComparisonLine(models.Model):
    _name = 'amortization.comparison.line'
    _description = 'Financial Comparative'

    amortization_id = fields.Many2one('amortization.calculator', string='Amortization', ondelete='cascade', required=True)
    plan_name = fields.Char(string="Plan")
    months = fields.Integer(string="Months")
    unit_price_discount = fields.Float(string="P.U. with discount")
    price_lot = fields.Float(string="Price without discount")
    discount_value = fields.Float(string="Discount")
    promotion_id = fields.Many2one('promotions.property', string="Promotion")
    initial_investment = fields.Float(string="Initial investment")
    gradual_initial_investment = fields.Float(string="Gradual Initial Investment")
    hitch_amount = fields.Float(string="Hitch")
    gradual_financing_amount = fields.Float(string="Amount to be Financed Gradual")
    financing_amount = fields.Float(string="Amount to finance")
    comparison_block_ids = fields.One2many('amortization.comparison.block', 'comparison_line_id', string="Blocks")


    @api.onchange('promotion_id')
    def _onchange_promotion_id(self):
        self._rebuild_blocks_with_promotion()

    def _rebuild_blocks_with_promotion(self):
        if not self.amortization_id or not self.amortization_id.payments or not self.promotion_id:
            return

        promotion_percent = self.promotion_id.porcent or 0.0
        price_meter = self.amortization_id.price_meter or 0.0
        meters = self.amortization_id.meters or 0.0
        hitch_percentage = self.amortization_id.hitch_percentage or 0.0

        discount_value = (price_meter * meters) * promotion_percent
        unit_price_discount = price_meter - (price_meter * promotion_percent)
        price_lot = price_meter * meters
        initial_investment = price_lot - discount_value
        gradual_initial = initial_investment
        hitch_amount = (gradual_initial * (hitch_percentage / 100.0)) * (1 - self.promotion_id.porcent_financial)
        hitch_no_discount = gradual_initial * (hitch_percentage / 100.0)
        gradual_financing = gradual_initial - hitch_no_discount
        financing_amount = price_lot - discount_value


        self.update({
            'discount_value': discount_value,
            'unit_price_discount': unit_price_discount,
            'initial_investment': initial_investment,
            'gradual_initial_investment': gradual_initial,
            'hitch_amount': hitch_amount,
            'gradual_financing_amount': gradual_financing,
            'financing_amount': financing_amount,
        })

        plan = self.amortization_id.payments.filtered(lambda p: p.name == self.plan_name)
        if not plan:
            return

        sorted_terms = sorted(plan.payment_term_ids, key=lambda t: t.end_month or 0)
        total_months = sorted_terms[-1].end_month if sorted_terms else 0
        current_debt = gradual_financing
        prev_end_month = 0
        blocks = []


        for term in sorted_terms:
            start_month = prev_end_month + 1
            end_month = term.end_month or 0
            duration = end_month - prev_end_month
            rate = term.interest or 0.0


            if duration <= 0:
                continue


            if rate == 0.0:
                pay_month = current_debt / float(total_months)
            else:
                month_rem = total_months - prev_end_month
                if month_rem <= 0:
                    month_rem = duration
                denom = 1.0 - math.pow(1.0 + rate, -month_rem)
                if abs(denom) < 1e-12:
                    pay_month = current_debt / float(duration)
                else:
                    pay_month = (current_debt * rate) / denom


            temp_debt = current_debt
            for i in range(duration):
                interest_amount = temp_debt * rate
                capital_amount = pay_month - interest_amount
                capital_amount = max(0.0, capital_amount)
                temp_debt = max(0.0, temp_debt - capital_amount)


            current_debt = temp_debt

            blocks.append((0, 0, {
                'block_name': f'Mensualidad {start_month} a {end_month}',
                'amount': round(pay_month, 2),
            }))

            prev_end_month = end_month

        self.comparison_block_ids = [(5, 0, 0)] + blocks


class AmortizationComparisonBlock(models.Model):
    _name = 'amortization.comparison.block'
    _description = 'Comparative monthly payment blocks'

    comparison_line_id = fields.Many2one('amortization.comparison.line', string='Comparative', ondelete='cascade', required=True)
    block_name = fields.Char(string='Block name')
    amount = fields.Float(string='Total amount')
