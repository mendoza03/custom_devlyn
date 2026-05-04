# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CommissionFactorSale(models.Model):
    _name = 'commission.factor.sale'
    _description = 'Commission factor sale'

    calculate_id = fields.Many2one(comodel_name='commission.calculate', string='Calculate')
    name = fields.Char(string='Name')
    factor = fields.Float(string='Factor')
    percentage = fields.Float(string='Percentage', digits=(2, 5))
    amount_total = fields.Float(string='Amount total')
    percentage_commission_upon_signing = fields.Float(string='Commission percentage upon signing the contract')
    commission_upon_signing = fields.Float(string='Commission upon signing the contract', compute='_compute_commissions', readonly=True)
    percentage_commission_on_the_deed = fields.Float(string='Commission percentage on the deed', compute='_compute_percentage_commission_on_the_deed', readonly=True)
    commission_on_the_deed = fields.Float(string='Commission on the deed', compute='_compute_commissions', readonly=True)

    @api.depends('percentage_commission_upon_signing', 'percentage_commission_on_the_deed')
    def _compute_commissions(self):
        for record in self:
            record.commission_upon_signing = (record.percentage_commission_upon_signing / 100) * record.amount_total
            record.commission_on_the_deed = (record.percentage_commission_on_the_deed / 100) * record.amount_total

    @api.depends('percentage_commission_upon_signing')
    def _compute_percentage_commission_on_the_deed(self):
        for record in self:
            record.percentage_commission_on_the_deed = 100 - record.percentage_commission_upon_signing

    @api.onchange('percentage_commission_upon_signing')
    def _onchange_percentage_commission_upon_signing(self):
        for record in self:
            if record.percentage_commission_upon_signing < 0 or record.percentage_commission_upon_signing > 100:
                raise ValidationError(_('The percentage must be between 0 and 100'))