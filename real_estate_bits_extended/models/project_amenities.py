# -*- coding: utf-8 -*-

from odoo import fields, models

import logging

_logger = logging.getLogger(__name__)


class ProjectAmenities(models.Model):
    _inherit = 'project.amenities'

    code = fields.Char(string='Code')