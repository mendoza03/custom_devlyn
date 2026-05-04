# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class RentStockPicking(models.Model):
    """Rent Stock Picking"""
    _inherit = 'stock.picking'
    _description = __doc__

    rent_order_id = fields.Many2one('rent.order', string="Rent Order")
    maintenance_request_id = fields.Many2one('maintenance.request', string="Maintenance Req")
    is_return_order = fields.Boolean()
