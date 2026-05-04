# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class EquipmentDeliveryImage(models.Model):
    """Equipment Delivery Image"""
    _name = 'equipment.delivery.image'
    _description = __doc__
    _rec_name = 'name'

    avatar = fields.Binary(string="Avatar")
    name = fields.Char(string="Name", required=True, translate=True, size=23)
    equipment_delivery_id = fields.Many2one('equipment.delivery',
                                            ondelete='cascade')


class EquipmentDelivery(models.Model):
    """Equipment Delivery"""
    _name = 'equipment.delivery'
    _description = __doc__
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Equipment",
                                 domain="[('can_be_rental', '=', True)]")
    product_qty = fields.Float(string="Quantity", default=1)
    deliver_order_id = fields.Many2one('stock.picking',
                                       string="Delivery Order")
    state = fields.Selection(related="deliver_order_id.state",
                             string="Status")
    description = fields.Char(string="Description")
    return_charge = fields.Monetary(string="Damage Charge")
    total_damage_charge = fields.Monetary(string=" Total Charges",
                                          compute='_compute_total_damage_charge')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    equipment_delivery_image_ids = fields.One2many(comodel_name='equipment.delivery.image',
                                                   inverse_name='equipment_delivery_id')
    rent_order_id = fields.Many2one('rent.order', ondelete='cascade')

    invoice_id = fields.Many2one('account.move', string="Damage Invoice")
    invoice_state = fields.Selection(related='invoice_id.payment_state', string=" Status")

    extra_hour_invoice_id = fields.Many2one('account.move', string="Extra Hour Invoice")
    extra_invoice_state = fields.Selection(related='extra_hour_invoice_id.payment_state', string=" Status ")

    is_any_extra_hours = fields.Boolean(string="Any Extra Hours")
    extra_hours = fields.Integer(string="Extra Hours")
    extra_hour_price = fields.Monetary(string="Extra Hour Price")
    total_charge = fields.Monetary(string="Total Charges",
                                   compute='_compute_total_charge')

    @api.onchange('is_any_extra_hours')
    def _onchange_is_any_extra_hours(self):
        """Onchange any extra hours"""
        self.extra_hours = ''
        self.extra_hour_price = ''
        self.total_charge = ''

    @api.depends('product_qty', 'return_charge')
    def _compute_total_damage_charge(self):
        """Compute Total Damage Charge"""
        for rec in self:
            rec.total_damage_charge = rec.product_qty * rec.return_charge

    @api.depends('extra_hours', 'extra_hour_price')
    def _compute_total_charge(self):
        """Compute Total Amount"""
        for rec in self:
            rec.total_charge = rec.extra_hours * rec.extra_hour_price

    def action_create_return_charge_invoice(self):
        """Create Return Damage Charge Invoice"""
        if not self.return_charge:
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': "Please add the necessary equipment return damage charges.",
                    'sticky': False,
                }
            }
            return message
        invoice_lines = []
        charge_invoice = {
            'product_id': self.product_id.id,
            'name': self.description,
            'quantity': self.product_qty,
            'price_unit': self.return_charge,
            'tax_ids': [],  # Changed from False to an empty list, which is usually the correct format
        }
        invoice_lines.append((0, 0, charge_invoice))
        data = {
            'partner_id': self.rent_order_id.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'rent_order_id': self.rent_order_id.id
        }
        invoice_id = self.env['account.move'].sudo().create(data)
        self.invoice_id = invoice_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice',
            'res_model': 'account.move',
            'res_id': invoice_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def action_create_extra_hour_invoice(self):
        """Create extra hour invoice"""
        if self.is_any_extra_hours:
            if not self.total_charge:
                message = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'warning',
                        'message': _(
                            """Kindly include the additional hours and corresponding extra hours' price details"""),
                        'sticky': False,
                    }
                }
                return message
            invoice_lines = []
            extra_hour_invoice = {
                'product_id': self.product_id.id,
                'name': self.description,
                'quantity': self.extra_hours,
                'price_unit': self.extra_hour_price,
                'tax_ids': [],  # Changed from False to an empty list, which is usually the correct format
            }
            invoice_lines.append((0, 0, extra_hour_invoice))
            data = {
                'partner_id': self.rent_order_id.customer_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
                'rent_order_id': self.rent_order_id.id
            }
            extra_hour_invoice_id = self.env['account.move'].sudo().create(data)
            self.extra_hour_invoice_id = extra_hour_invoice_id.id
            return {
                'type': 'ir.actions.act_window',
                'name': 'Extra Hour Invoice',
                'res_model': 'account.move',
                'res_id': extra_hour_invoice_id.id,
                'view_mode': 'form',
                'target': 'current'
            }
