# -*- coding: utf-8 -*-

from odoo import fields, models

import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_additional_expense = fields.Boolean(string='Is additional expense')
    additional_expense_ids = fields.One2many(comodel_name='project.property.additional', inverse_name='property_id', string='Additional expenses', copy=True, auto_join=True)