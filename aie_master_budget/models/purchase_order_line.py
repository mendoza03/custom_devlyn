# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools.logger_config import configure_logger

_logger = configure_logger()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    task_id = fields.Many2one(comodel_name='master.budget.line', string='Task')
    concept_id = fields.Many2one(comodel_name='master.budget.line', string='Concept')
    budget_item_id = fields.Many2one(comodel_name='master.budget.line', string='Budget Item')
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id')

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('task_id')
    def onchange_task_id(self):
        self.concept_id = False

    @api.onchange('concept_id')
    def onchange_concept_id(self):
        self.budget_item_id = False

    @api.onchange('budget_item_id', 'product_qty', 'price_unit', 'taxes_id', 'price_total')
    def _onchange_budget_item_id(self):
        for record in self:
            if record.budget_item_id:
                lines = self.env['purchase.order.line'].search([('budget_item_id', '=', record.budget_item_id.id)])
                total = 0.0
                company_currency = record.budget_item_id.company_id.currency_id
                if not record._origin:
                    total += record.price_total
                else:
                    lines = lines.filtered(lambda line: line.id != record.id)
                    total += record.price_total
                for line in lines:
                    purchase_currency = line.currency_id
                    amount = line.price_total
                    if purchase_currency != company_currency:
                        amount = purchase_currency._convert(
                            amount,
                            company_currency,
                            record.company_id,
                            line.order_id.date_order or fields.Date.today()
                        )
                    total += amount
                if total > record.budget_item_id.amount_residual:
                    raise UserError('La cantidad utilizada excede el monto disponible($%s) en el presupuesto' % record.budget_item_id.price_total)

    @api.onchange('product_id')
    def onchange_product_id(self):
        super().onchange_product_id()
        self.budget_item_id = False