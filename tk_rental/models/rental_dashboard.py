# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class RentalDashboard(models.Model):
    """Rental Dashboard"""
    _name = "rental.dashboard"
    _description = __doc__

    @api.model
    def get_rental_dashboard(self):
        rent_orders = self.env['rent.order'].sudo()
        stock_picking = self.env['stock.picking'].sudo()

        total_rent_orders = rent_orders.search_count([])
        draft_stages = rent_orders.search_count([('status', '=', 'draft')])
        quotation_stages = rent_orders.search_count([('status', '=', 'quotation')])
        quotation_sent_stages = rent_orders.search_count([('status', '=', 'quotation_sent')])
        quotation_approve = rent_orders.search_count([('status', '=', 'approve')])
        reject_stages = rent_orders.search_count([('status', '=', 'reject')])
        in_progress_stages = rent_orders.search_count([('status', '=', 'in_progress')])
        in_delivery_stages = rent_orders.search_count([('status', '=', 'in_delivery')])
        return_stages = rent_orders.search_count([('status', '=', 'return')])
        closed_orders = rent_orders.search_count([('status', '=', 'close')])
        cancel_orders = rent_orders.search_count([('status', '=', 'cancel')])

        delivery_orders = stock_picking.search_count(
            [('state', '!=', 'done'), ('rent_order_id', '!=', False), ('is_return_order', '=', False)])
        done_delivery_orders = stock_picking.search_count(
            [('state', '=', 'done'), ('rent_order_id', '!=', False), ('is_return_order', '=', False)])

        return_orders = stock_picking.search_count(
            [('state', '!=', 'done'), ('rent_order_id', '!=', False), ('is_return_order', '!=', False)])
        return_delivery_orders = stock_picking.search_count(
            [('state', '=', 'done'), ('rent_order_id', '!=', False), ('is_return_order', '!=', False)])

        rent_order_status = [
            ['Nuevo', 'Cotización', 'Cotización Enviada', 'Cotización Aprobada', 'Rechazar', 'En Progreso', 'Entrega Pendiente',
             'Devoluciones', 'Cerrado', 'Cancelado', 'Órdenes de Entrega en Borrador', 'Órdenes de Entrega Completadas',
             'Órdenes de Devolución en Borrador', 'Órdenes de Devolución Completadas'],
            [draft_stages, quotation_stages, quotation_sent_stages, quotation_approve, reject_stages,
             in_progress_stages, in_delivery_stages, return_stages, closed_orders, cancel_orders,
             delivery_orders, done_delivery_orders, return_orders, return_delivery_orders]
        ]

        data = {
            'total_rent_orders': total_rent_orders,
            'draft_stages': draft_stages,
            'quotation_stages': quotation_stages,
            'quotation_sent_stages': quotation_sent_stages,
            'quotation_approve': quotation_approve,
            'reject_stages': reject_stages,
            'in_progress_stages': in_progress_stages,
            'in_delivery_stages': in_delivery_stages,
            'return_stages': return_stages,
            'closed_orders': closed_orders,
            'cancel_orders': cancel_orders,
            'delivery_orders': delivery_orders,
            'done_delivery_orders': done_delivery_orders,
            'return_orders': return_orders,
            'return_delivery_orders': return_delivery_orders,
            'rent_order_status': rent_order_status,
        }
        return data
