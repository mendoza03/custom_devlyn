# -*- coding: utf-8 -*-

from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ProjectPropertyAdditional(models.Model):
    _name = 'project.property.additional'
    _description = 'Additional expense'

    property_id = fields.Many2one(comodel_name='product.template', string='Property', required=True, ondelete='cascade', index=True, copy=False)
    product_id = fields.Many2one(comodel_name='product.template', string='Product', change_default=True, ondelete='restrict', index='btree_not_null', domain="[('is_additional_expense', '=', True)]")
    price_subtotal = fields.Float(string='Subtotal', compute='_compute_amount', store=True, precompute=True)

    @api.depends('product_id')
    def _compute_amount(self):
        for line in self:
            line.update({
                'price_subtotal': line.product_id.list_price if line.product_id else 0,
            })