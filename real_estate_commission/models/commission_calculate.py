# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.fields import Command

import logging

_logger = logging.getLogger(__name__)


class CommissionCalculate(models.Model):
    _name = 'commission.calculate'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _description = 'Calculate'

    name = fields.Char(string='Name', default=_('New'), readonly=True)
    property_id = fields.Many2one(comodel_name='product.template', string='Property')
    worksite_id = fields.Many2one(comodel_name='project.worksite', related='property_id.worksite_id')
    create_date = fields.Datetime(string="Creation Date", index=True, readonly=True)
    contract_id = fields.Many2one(comodel_name='property.contract', string='Contract')
    order_id = fields.Many2one('sale.order', string='order', related='contract_id.order_id')
    opportunity_id = fields.Many2one('crm.lead', string='Lead', readonly=True)
    advance_payment_date = fields.Date(string='Down payment date', related='contract_id.advance_payment_date')
    date_start = fields.Date(string='Start date', related='contract_id.date')
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel'),
    ], default='draft', string='State', readonly=True)
    commission_percentage = fields.Float()
    amount = fields.Float(string='Amount')
    scenary_id = fields.Many2one(comodel_name='commission.scenary', string='Scenary')
    total_commission = fields.Float(string='Total commission', readonly=True, compute='_compute_total_commission')
    percentage_commission_upon_signing = fields.Float(string='Commission percentage upon signing the contract')
    commission_upon_signing = fields.Float(string='Commission upon signing the contract', compute='_compute_commissions', readonly=True)
    percentage_commission_on_the_deed = fields.Float(string='Commission percentage on the deed')
    commission_on_the_deed = fields.Float(string='Commission on the deed', compute='_compute_commissions', readonly=True)
    factor_sale_line_ids = fields.One2many(comodel_name='commission.factor.sale', inverse_name='calculate_id', string='Lines')

    invoice_commission_upon_signing_id = fields.Many2one(comodel_name='account.move', string='Commission upon signing invoice')
    invoice_commission_on_the_deed_id = fields.Many2one(comodel_name='account.move', string='Commission on the deed invoice')
    advance_payment_payment_id = fields.Many2one("account.payment", string="Advance Payment", related='contract_id.advance_payment_payment_id')


    @api.depends('commission_percentage', 'amount')
    def _compute_total_commission(self):
        for record in self:
            record.total_commission = 0
            if record.commission_percentage and record.amount:
                record.total_commission = record.amount * (record.commission_percentage / 100)

    @api.onchange('commission_percentage', 'amount', 'factor_sale_line_ids')
    def _onchange_commission_fields(self):
        for record in self:
            for line in record.factor_sale_line_ids:
                line.percentage = (record.commission_percentage / 100) * (line.factor / 100)
                line.amount_total = record.amount * (line.percentage)

    @api.depends('percentage_commission_upon_signing', 'percentage_commission_on_the_deed')
    def _compute_commissions(self):
        for record in self:
            record.commission_upon_signing = (record.percentage_commission_upon_signing / 100) * record.total_commission
            record.commission_on_the_deed = (record.percentage_commission_on_the_deed / 100) * record.total_commission

    def action_load_commissions(self):
        for record in self:
            record.factor_sale_line_ids.unlink()
            for line in record.scenary_id.factor_line_ids:
                record.write({
                    'factor_sale_line_ids': [(0, 0, {
                        'name': line.name,
                        'factor': line.factor,
                        'percentage_commission_upon_signing': line.default_percentage_commission_upon_signing,
                    })],
                })
            record.percentage_commission_upon_signing = self.env.company.commission_upon_signing
            record.percentage_commission_on_the_deed = self.env.company.commission_on_the_deed
            record._onchange_commission_fields()

    def action_confirm(self):
        self.write({
            'name': self.property_id.display_name,
            'state': 'confirm',
        })

    def action_create_invoice_commission_upon_signing(self):
        invoice_id = self.env['account.move'].create(self._prepare_invoice(self.commission_upon_signing))
        self.write({
            'invoice_commission_upon_signing_id': invoice_id.id,
        })
        return self.action_view_invoice_commission_upon_signing()

    def action_view_invoice_commission_upon_signing(self):
        return self.show_invoice(self.invoice_commission_upon_signing_id.id)

    def action_create_invoice_commission_on_the_deed(self):
        invoice_id = self.env['account.move'].create(self._prepare_invoice(self.commission_on_the_deed))
        self.write({
            'invoice_commission_on_the_deed_id': invoice_id.id,
        })
        return self.action_view_invoice_commission_on_the_deed()

    def action_view_invoice_commission_on_the_deed(self):
        return self.show_invoice(self.invoice_commission_on_the_deed_id.id)

    def _prepare_invoice(self, price_unit=0):
        return {
            'invoice_origin': self.name,
            # 'journal_id': self.session_id.config_id.invoice_journal_id.id,
            'move_type': 'out_invoice',
            'ref': self.name,
            'partner_id': self.property_id.partner_id.id if self.property_id.partner_id else False,
            # 'invoice_user_id': self.user_id.id,
            'invoice_line_ids': [Command.create(self._prepare_invoice_line(price_unit))],
            'invoice_payment_term_id': self.property_id.partner_id.property_payment_term_id.id or False,
        }

    def _prepare_invoice_line(self, price_unit):
        return {
            'product_id': self.property_id.id,
            'quantity': 1,
            'price_unit': price_unit,
            'name': self.name,
            'tax_ids': [(6, 0, self.property_id.taxes_id.ids)],
            'product_uom_id': self.property_id.uom_id.id,
        }

    def show_invoice(self, id):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form,list',
            'res_model': 'account.move',
            'res_id': id,
        }