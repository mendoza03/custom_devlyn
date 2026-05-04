# -*- coding: utf-8 -*-

from odoo import fields, models


class CommissionScenary(models.Model):
    _name = 'commission.scenary'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = 'Commission scenary'

    name = fields.Char(string='Name')
    factor_line_ids = fields.One2many(comodel_name='commission.factor', inverse_name='scenary_id', string='Lines')
