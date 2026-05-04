# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)

class Property(models.Model):
    _inherit = 'product.template'
    
    estimated_date = fields.Date(string='Estimated date')
    property_date = fields.Date('Date', default=False)
    terrain_type = fields.Selection(selection=[
        ('standard_a', 'Standard A'), 
        ('standard_aa', 'Standard AA'),
        ('standard_aaa', 'Standard AAA'),
        ('premium_a', 'Premium A'),
        ('premium_aa', 'Premium AA'),
        ('premium_aaa', 'Premium AAA'),
    ], string='Terrain type')
    external_initial_maintenance_fee = fields.Float(string='External initial maintenance fee')
    external_amenity_maintenance_fee = fields.Float(string='External amenity maintenance fee')
    external_maximum_maintenance_fee = fields.Float(string='External maximum maintenance fee')
    property_area = fields.Float(digits=(16, 2))

    @api.depends('name','default_code')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.name} [{rec.default_code}]'