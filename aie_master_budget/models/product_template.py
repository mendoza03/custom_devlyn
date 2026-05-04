# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    has_admin_access_master_budget = fields.Boolean(string='Has Admin Access Master Budget', compute='_compute_has_admin_access_master_budget')
    budget_price_unit = fields.Float(string='Unit price for budget', digits='Product Price')

    def _compute_has_admin_access_master_budget(self):
        for record in self:
            record.has_admin_access_master_budget = self.env.user.has_group('aie_master_budget.group_access_aie_master_budget_admin')