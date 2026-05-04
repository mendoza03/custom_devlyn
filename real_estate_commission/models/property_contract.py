# -*- coding: utf-8 -*-

from odoo import fields, models

import logging

_logger = logging.getLogger(__name__)


class PropertyContract(models.Model):
    _inherit = 'property.contract'

    commission_id = fields.Many2one(comodel_name='commission.calculate', string='Commission')

    def action_confirm(self):
        super().action_confirm()
        for record in self:
            if record.property_id:
                commission_id = self.env['commission.calculate'].create({
                    'property_id': record.property_id.id,
                    'amount': record.pricing,
                })
                record.write({
                    'commission_id': commission_id.id,
                })
                if self.env.user.sudo().has_group('real_estate_commission.group_commission_manager'):
                    return {
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form,list',
                        'res_model': 'commission.calculate',
                        'res_id': commission_id.id,
                    }

    def action_view_commission(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form,list',
            'res_model': 'commission.calculate',
            'res_id': self.commission_id.id,
        }
