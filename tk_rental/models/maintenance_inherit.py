# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class MaintenanceEquipment(models.Model):
    """Maintenance Equipment"""
    _inherit = 'maintenance.equipment'
    _description = __doc__

    product_id = fields.Many2one('product.product', string="Equipment",
                                 domain="[('can_be_rental', '=', True)]")
    customer_id = fields.Many2one('res.partner', string="Customer")

    def action_create_maintenance_request(self):
        """Create Maintenance Request"""
        data = {
            'name': 'Maintenance Request For ' + self.name,
            'customer_id': self.customer_id.id,
            'product_id': self.product_id.id,
            'description': self.note,
            'equipment_id': self.id,
        }
        equipment_id = self.env['maintenance.request'].create(data)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Request'),
            'res_model': 'maintenance.request',
            'res_id': equipment_id.id,
            'view_mode': 'form',
            'target': 'current'
        }


class MaintenanceSparePart(models.Model):
    """Maintenance Spare Part"""
    _name = 'maintenance.spare.part'
    _description = __doc__
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Spare Part",
                                 domain="[('type', '=', 'consu')]")
    qty = fields.Float(string="Quantity", default=1)
    price = fields.Monetary(string="Price")
    sub_total = fields.Monetary(string="Sub Total",
                                compute='_compute_total_part_price')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    maintenance_request_id = fields.Many2one('maintenance.request',
                                             ondelete='cascade')

    @api.onchange('product_id')
    def _onchange_part_price(self):
        """Onchange Part Price"""
        for rec in self:
            rec.price = rec.product_id.lst_price

    @api.depends('qty', 'price')
    def _compute_total_part_price(self):
        """Compute Total Part Price"""
        for rec in self:
            rec.sub_total = rec.qty * rec.price


class MaintenanceService(models.Model):
    """Maintenance Service"""
    _name = 'maintenance.service'
    _description = __doc__
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Service",
                                 domain="[('type', '=', 'service')]")
    service_charge = fields.Monetary(string="Service Charge")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    maintenance_request_id = fields.Many2one('maintenance.request',
                                             ondelete='cascade')

    @api.onchange('product_id')
    def _onchange_service_charge(self):
        """Onchange Service Charge"""
        for rec in self:
            rec.service_charge = rec.product_id.lst_price


class MaintenanceRequest(models.Model):
    """Maintenance Request"""
    _inherit = 'maintenance.request'
    _description = __doc__

    product_id = fields.Many2one('product.product', string=" Equipment",
                                 domain="[('can_be_rental', '=', True)]")
    customer_id = fields.Many2one('res.partner', string="Customer")
    maintenance_spare_part_ids = fields.One2many(comodel_name='maintenance.spare.part',
                                                 inverse_name='maintenance_request_id')
    maintenance_service_ids = fields.One2many(comodel_name='maintenance.service',
                                              inverse_name='maintenance_request_id')
    total_part_price = fields.Monetary(compute='_compute_total_part_price',
                                       string="Spare Part Price")
    total_service_charge = fields.Monetary(compute='_compute_service_charge',
                                           string="Service Charge")
    total = fields.Monetary(compute='_compute_total_charge',
                            string="Total")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    invoice_id = fields.Many2one('account.move')
    total_invoiced = fields.Monetary(string=" Total",
                                     related="invoice_id.amount_total")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    delivery_order_id = fields.Many2one('stock.picking')
    order_count = fields.Integer(string="Delivery Orders",
                                 compute='_compute_order_count')

    @api.depends('maintenance_spare_part_ids.price', 'maintenance_spare_part_ids.qty')
    def _compute_total_part_price(self):
        """Total Spare Parts Price"""
        for rec in self:
            rec.total_part_price = sum(part.price * part.qty for part in rec.maintenance_spare_part_ids)

    @api.depends('maintenance_service_ids.service_charge')
    def _compute_service_charge(self):
        """Total Service Charges"""
        for rec in self:
            rec.total_service_charge = sum(service.service_charge for service in rec.maintenance_service_ids)

    @api.depends('total_part_price', 'total_service_charge')
    def _compute_total_charge(self):
        """Total Charge"""
        for rec in self:
            rec.total = rec.total_part_price + rec.total_service_charge

    def action_create_maintenance_invoice(self):
        """Create Maintenance Invoice"""
        if not self.maintenance_spare_part_ids or not self.maintenance_service_ids:
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': "Please add the required parts and services.",
                    'sticky': False,
                }
            }
            return message
        invoice_lines = []
        for rec in self.maintenance_spare_part_ids:
            part = {
                'product_id': rec.product_id.id,
                'name': rec.product_id.name,
                'quantity': rec.qty,
                'price_unit': rec.price,
            }
            invoice_lines.append((0, 0, part))
        val = (0, 0, {
            'display_type': 'line_section',
            'name': "Services",
        })
        invoice_lines.append(val)
        for data in self.maintenance_service_ids:
            service_data = {
                'product_id': data.product_id.id,
                'name': data.product_id.name,
                'quantity': 1,  # Assuming services are billed as a single unit
                'price_unit': data.service_charge,
            }
            invoice_lines.append((0, 0, service_data))
        data = {
            'partner_id': self.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'maintenance_request_id': self.id
        }
        invoice_id = self.env['account.move'].sudo().create(data)
        invoice_id.action_post()
        self.invoice_id = invoice_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': invoice_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def action_maintenances_invoice_view(self):
        """Maintenance Invoice View"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'create': False,
            }
        }

    def action_create_delivery_order(self):
        """Create Delivery Order"""
        if not self.maintenance_spare_part_ids:
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': "Please add the required parts",
                    'sticky': False,
                }
            }
            return message
        lines = []
        for line in self.maintenance_spare_part_ids:
            lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.qty,
                'product_uom': line.product_id.uom_id.id,
                'location_id': self.warehouse_id.lot_stock_id.id,
                'location_dest_id': self.warehouse_id.wh_output_stock_loc_id.id,
                'name': line.product_id.name
            }))
        delivery_record = {
            'partner_id': self.customer_id.id,
            'picking_type_id': self.warehouse_id.out_type_id.id,
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.warehouse_id.wh_output_stock_loc_id.id,
            'move_ids_without_package': lines,
            'move_type': 'one',
            'maintenance_request_id': self.id,
        }
        delivery_order_id = self.env['stock.picking'].create(delivery_record)
        self.delivery_order_id = delivery_order_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Delivery Order',
            'res_model': 'stock.picking',
            'res_id': delivery_order_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def _compute_order_count(self):
        """Compute Delivery Order Count"""
        for rec in self:
            rec.order_count = self.env['stock.picking'].search_count([('maintenance_request_id', '=', rec.id)])

    def action_order_view(self):
        """Delivery Order Views"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivery Orders'),
            'res_model': 'stock.picking',
            'domain': [('maintenance_request_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'current',
            'context': {
                'create': False,
            }
        }
