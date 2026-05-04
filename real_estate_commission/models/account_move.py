# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    commission_upon_signing_id = fields.One2many(comodel_name='commission.calculate', inverse_name='invoice_commission_upon_signing_id', string='Commission upon signing')
    commission_on_the_deed_id = fields.One2many(comodel_name='commission.calculate', inverse_name='invoice_commission_on_the_deed_id', string='Commission on the deed')

    def action_show_commission(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form,list',
            'res_model': 'commission.calculate',
            'res_id': self.commission_upon_signing_id.id if self.commission_upon_signing_id else
                      self.commission_on_the_deed_id.id if self.commission_on_the_deed_id else False,
        }