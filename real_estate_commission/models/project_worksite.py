# -*- coding: utf-8 -*-

from odoo import fields, models

import logging

_logger = logging.getLogger(__name__)


class ProjectWorksite(models.Model):
    _inherit = 'project.worksite'

    commission_percentage = fields.Float(string='Commission percentage')
    commission_percentage_parent = fields.Float()