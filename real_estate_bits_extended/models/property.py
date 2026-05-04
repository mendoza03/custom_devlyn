# -*- coding: utf-8 -*-

from odoo import fields, models

import logging

_logger = logging.getLogger(__name__)


class Property(models.Model):
    _inherit = 'product.template'

    number_bedrooms = fields.Integer(string='Number of bedrooms')
    number_bathrooms = fields.Float(string='Number of bathrooms')