# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import fields, api, models


class EquipmentOdometer(models.Model):
    """Equipment Odometer History"""
    _name = 'equipment.odometer'
    _description = __doc__
    _order = 'create_date DESC'

    product_id = fields.Many2one('product.product',
                                 domain=[('is_vehicle', '=', True)],
                                 string='Equipment')
    current_readings = fields.Float("Current Reading")
    last_readings = fields.Float("Last Reading")
    unit = fields.Selection([('kilometer', 'km'), ('miles', 'mi')], "Unit")
