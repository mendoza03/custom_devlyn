# -*- coding: utf-8 -*-

from ..tools.logger_config import configure_logger

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = configure_logger()


class MasterBudgetLineUpdate(models.TransientModel):
    _name = 'master.budget.line.update'
    _description = 'Update Budget Line'

    budget_id = fields.Many2one(comodel_name='master.budget', string='Budget')
    domain_product_ids = fields.Many2many('product.template', string='Products for domain')
    product_id = fields.Many2one(comodel_name='product.template', string='Product')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'master.budget':
            if len(self.env.context.get('active_ids', [])) > 1:
                raise UserError(_("You can only change the price on one budget at a time."))
            budget = self.env['master.budget'].browse(self.env.context.get('active_id'))
            if budget.exists():
                res.update({
                    'budget_id': budget.id,
                    'domain_product_ids': [(6, 0, budget.line_ids.product_id.ids)],
                })
        return res

    def action_confirm(self):
        for line in self.budget_id.line_ids.filtered(lambda line: line.product_id == self.product_id):
            line.write({
                'price_unit': self.price_unit,
            })