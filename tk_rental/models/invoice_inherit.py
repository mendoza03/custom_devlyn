# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class RentalInvoice(models.Model):
    """Rental Invoice"""
    _inherit = 'account.move'
    _description = __doc__

    rent_order_id = fields.Many2one('rent.order', string="Rent Order")
    maintenance_request_id = fields.Many2one('maintenance.request',
                                             string="Maintenance Req")
