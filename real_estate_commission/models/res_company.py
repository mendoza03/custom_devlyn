# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    commission_upon_signing = fields.Float(string='Commission upon signing the contract', default=50)
    commission_on_the_deed = fields.Float(string='Commission on the deed', default=50)