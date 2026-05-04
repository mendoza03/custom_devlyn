from odoo import models, _, api, fields
from logging import getLogger
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

_log = getLogger(__name__)

class InheritPropertyReservation(models.Model):
    _inherit = 'property.reservation'


    order_id = fields.Many2one('sale.order', string="Order Id")
    currency_id = fields.Many2one('res.currency', string="Currency Id")
    net_price = fields.Float(related='property_id.net_price')
    price_total= fields.Float()

    def _validate_voucher_attachment(self):
        attachment = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
        ], limit=1)

        if not attachment:
            raise ValidationError(_("Voucher attachment is required before generating the contract."))

    def action_confirm(self):
        for reservation in self:
            reservation._validate_voucher_attachment()
        return super().action_confirm()

    def action_contract_ownership(self):
        finance_id = self.order_id.financial_lines.filtered(lambda x: x.name == self.order_id.finance_id.name)
        line_hitch = self.order_id.hitch_ids.filtered(lambda x: x.finance_id.id == finance_id.id)
        contract_date = self.contract_date

        day = contract_date.day
        if 1 <= day <= 5:
            new_date = contract_date + relativedelta(months=1)
        else:
            new_date = (contract_date.replace(day=1) + relativedelta(months=2))

        print('price_total', self.price_total)

        contract = self.env['property.contract'].create({
                "contract_type": "is_ownership",
                "project_id": self.project_id.id,
                "partner_id": self.partner_id.id,
                "property_id": self.property_id.id,
                "property_type_id":self.property_type_id.id,
                "type": self.type,
                "pricing": self.price_total,
                "real_total": self.price_total,
                "price_per_m": self.price_per_m,
                "advance_payment_type": 'percentage',
                "reservation_id": self.id,
                "deposit": self.deposit,
                'currency_id':self.order_id.currency_id.id,
                "advance_payment_type": self.advance_payment_type,
                'order_id':self.order_id.id,
                'periodicity_hitch': line_hitch.period_payment,
                'is_difered_hitch': self.order_id.difer_hitch,
                'hitch_difered_months': self.order_id.val_defer,
                'template_id': self.order_id.finance_id.id,
                'pricing': finance_id.amount_total,
                'advance_payment_rate': finance_id.hitch_porcent * 100,
                'advance_payment': finance_id.hitch,
                'insurance_fee': 0,
                'date_payment': new_date,
                'date': new_date,
            })
        contract.action_calculate()

        first_month_line = contract.loan_line_ids.filtered(
            lambda line: line.count_line == 1
        )[:1]
        if first_month_line and 'date_fist_month' in self.property_id._fields:
            self.property_id.write({
                'date_fist_month': first_month_line.date,
            })

        return {
            "name": _("Ownership Contract"),
            "view_type": "form",
            "view_mode": "form",
            "res_model": "property.contract",
            "view_id": self.env.ref("real_estate_bits.view_property_contract_form").id,
            "type": "ir.actions.act_window",
            "res_id": contract.id,
            "target": "current",
        }

    def send_email_template_reservation(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        mail_template = self.env.ref('real_state_bits_finance_quote.email_template_property_reservation')
        ctx = {
            'default_model': 'property.reservation',
            'default_res_ids': self.ids,
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            # 'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'force_email': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }
