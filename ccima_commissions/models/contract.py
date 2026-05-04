from odoo import models, fields, api, _


class PropertyContract(models.Model):
    _inherit = 'property.contract'

    def _get_promotion_from_sale_order(self, order):
        if not order:
            return False

        finance_plan = getattr(order, 'finance_id', False)
        financial_lines = getattr(order, 'financial_lines', False)

        if not finance_plan or not financial_lines:
            return False

        match = financial_lines.filtered(lambda l: (l.name or '') == (finance_plan.name or ''))[:1]
        if not match:
            return False

        promo = getattr(match, 'promotion_id', False)
        return promo if promo else False

    def action_confirm(self):
        result = super(PropertyContract, self).action_confirm()

        Commission = self.env['ccima.commissions']
        Brief = self.env['rev.crm.contract.brief'].sudo()

        for contract in self:
            reservation = getattr(contract, 'reservation_id', False)
            if not reservation:
                continue

            order = getattr(reservation, 'order_id', False)
            if not order:
                continue

            lead = getattr(order, 'opportunity_id', False)
            if not lead:
                continue


            advance_payment = getattr(contract, 'advance_payment_payment_id', False)
            if not advance_payment:
                continue


            property_name = False
            ref_name = False
            if getattr(lead, 'property_id', False):
                property_name = lead.property_id.name or False
                ref_name = lead.property_id.default_code or False

            commission_name = 'comisiones '
            if property_name:
                commission_name += property_name
            else:
                commission_name += (lead.name or '')

            brief = Brief.search([('lead_id', '=', lead.id)], limit=1)
            if not brief:
                continue
            if not brief.have_contract:
                continue
            if brief.have_commission:
                continue

            promo = self._get_promotion_from_sale_order(order)
            promo_name = ''
            if promo:
                promo_name = promo.name

            vals = {
                'lead_id': lead.id,
                'name': commission_name,
                'promotion_name': promo_name,
                'reference': ref_name,
                'deposit': getattr(reservation, 'deposit', 0.0) or 0.0,
                'deposit_date': getattr(reservation, 'date', False),
                'contract_date': self.date,
            }

            commission = Commission.create(vals)

            commission._onchange_lead_id()

            commission.action_calculate_lines()

            brief.write({'have_commission': True})

        return result


class HREmployee(models.Model):
    _inherit = 'hr.employee'


    payment_type = fields.Char(string='Payment Type')


