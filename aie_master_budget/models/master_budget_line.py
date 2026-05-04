# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from ..tools.logger_config import configure_logger

_logger = configure_logger()


class MasterBudgetLine(models.Model):
    _name = 'master.budget.line'
    _description = 'Master Budget Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'short_name'

    active = fields.Boolean(string='Active', default=True)
    budget_id = fields.Many2one(comodel_name='master.budget', string='Budget', required=True, ondelete='cascade', copy=False)
    budget_project_id = fields.Many2one(related='budget_id.project_id', store=False)
    short_name = fields.Char(string='Short name', compute='_compute_complete_name', store=True)
    complete_name = fields.Char(string='Complete name', compute='_compute_complete_name', recursive=True, store=True)
    type = fields.Selection([
        ('budget_item', 'Budget Item'),
        ('concept', 'Concept'),
        ('task', 'Task'),
        ('project', 'Project'),
    ], string='Type', default='budget_item')
    parent_id = fields.Many2one(comodel_name='master.budget.line', string='Parent', ondelete='cascade')
    child_ids = fields.One2many(comodel_name='master.budget.line', inverse_name='parent_id', string='Child lines', ondelete='cascade')
    code = fields.Char(string='Code')
    name = fields.Char(string='Name')
    project_id = fields.Many2one(comodel_name='project.project', string='Project')
    task_id = fields.Many2one(comodel_name='project.task', string='Task')
    product_id = fields.Many2one(comodel_name='product.template', string='Product')
    price_unit = fields.Float(string='Unit Price', digits='Product Price')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure')
    quantity_use_manual = fields.Float(string='Quantity manual')
    quantity_use = fields.Float(string='Quantity Use', digits='Product Unit of Measure', compute='_compute_quantity_use')
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', depends=['product_id'])
    product_uom = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure', ondelete='restrict', domain='[("category_id", "=", product_uom_category_id)]')
    price_subtotal = fields.Float(string='Subtotal', digits='Product Price', compute='_compute_price_subtotal')
    price_total = fields.Float(string='Total', digits='Product Price', compute='_compute_price_total')
    amount_use = fields.Float(digits='Product Price', compute='_compute_amount_use', string='Amount use')
    amount_use_manual = fields.Float(digits='Product Price', string='Amount use manual')
    amount_residual = fields.Float(string='Residual', compute='_compute_amount_residual')
    performance = fields.Float(string="performance")

    purchase_line_ids = fields.One2many(comodel_name='purchase.order.line', inverse_name='budget_item_id', string='Purchase Order Lines')

    company_id = fields.Many2one(related='budget_id.company_id', store=True, index=True, precompute=True)

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------

    def unlink(self):
        for record in self:
            if record.child_ids:
                record.child_ids.unlink()
        return super().unlink()

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('code', 'name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for record in self:
            name = ''
            if record.code and record.name:
                name = '%s - %s' % (record.code, record.name)
            else:
                name = record.name
            record.short_name = name
            if record.parent_id:
                record.complete_name = '%s / %s' % (record.parent_id.complete_name, record.short_name)
            else:
                record.complete_name = record.short_name

    @api.depends('price_unit', 'quantity', 'product_uom')
    def _compute_price_subtotal(self):
        for record in self:
            record.price_subtotal = record.price_unit * record.quantity

    @api.depends('price_subtotal', 'price_total', 'type')
    def _compute_price_total(self):
        for record in self.filtered(lambda record: not record.type):
            record.price_total = 0
        for record in self.filtered(lambda record: record.type == 'budget_item'):
            record.price_total = record.price_subtotal
        for record in self.filtered(lambda record: record.type == 'concept'):
            total = sum(record.child_ids.mapped('price_subtotal'))
            record.price_unit = total 
            record.price_total = record.quantity * total

        for record in self.filtered(lambda record: record.type == 'task'):
            record.price_total = sum(record.child_ids.mapped('price_total'))
        for record in self.filtered(lambda record: record.type == 'project'):
            record.price_total = sum(record.child_ids.mapped('price_total'))

    @api.depends('purchase_line_ids.product_uom', 'purchase_line_ids.product_qty')
    def _compute_quantity_use(self):
        for record in self:
            qty = record.quantity_use_manual
            for purchase_line in record.purchase_line_ids:
                qty += purchase_line.product_uom._compute_quantity(
                    purchase_line.product_qty, record.product_uom,
                )
            record.quantity_use = qty

    @api.depends('purchase_line_ids.price_total')
    def _compute_amount_use(self):
        for record in self:
            total = record.amount_use_manual
            if record.type == 'budget_item':
                company_currency = record.company_id.currency_id
                for line in record.purchase_line_ids:
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
            record.amount_use = total

    @api.depends('price_total', 'amount_use')
    def _compute_amount_residual(self):
        for record in self:
            record.amount_residual = record.price_total - record.amount_use

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('type')
    def _onchange_type(self):
        for record in self:
            record.parent_id = False
            record.project_id = False
            record.task_id = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for record in self:
            record.product_uom = record.product_id.uom_id.id if record.product_id else False
            record.price_unit = record.product_id.budget_price_unit if record.product_id else False

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    def action_open_purchases(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Órdenes de compra',
            'res_model': 'purchase.order',
            'views': [[False, 'list'], [False, 'form']],
            'domain': [('id', 'in', self.purchase_line_ids.order_id.ids)],
        }
