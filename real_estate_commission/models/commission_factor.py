# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CommissionFactor(models.Model):
    _name = 'commission.factor'
    _description = 'Commission factor'

    scenary_id = fields.Many2one(comodel_name='commission.scenary', string='Scenary')
    name = fields.Char(string='Name')
    factor = fields.Float(string='Factor')
    default_percentage_commission_upon_signing = fields.Float(string='Commission percentage upon signing the contract', default=50)
    default_percentage_commission_on_the_deed = fields.Float(string='Commission percentage on the deed', compute='_compute_default_percentage_commission_on_the_deed', readonly=True)

    @api.depends('default_percentage_commission_upon_signing')
    def _compute_default_percentage_commission_on_the_deed(self):
        for record in self:
            record.default_percentage_commission_on_the_deed = 100 - record.default_percentage_commission_upon_signing

    @api.onchange('default_percentage_commission_upon_signing')
    def _onchange_default_percentage_commission_upon_signing(self):
        for record in self:
            if record.default_percentage_commission_upon_signing < 0 or record.default_percentage_commission_upon_signing > 100:
                raise ValidationError(_('The percentage must be between 0 and 100'))