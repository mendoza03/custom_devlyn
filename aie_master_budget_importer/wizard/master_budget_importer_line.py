# -*- coding: utf-8 -*-

from odoo import api, fields, models

import json
import logging

_logger = logging.getLogger(__name__)


class MasterBudgetImporterLine(models.TransientModel):
    _name = 'master.budget.importer.line'
    _description = 'Master Budget Importer Line'

    budget_importer_id = fields.Many2one(comodel_name='master.budget.importer', string='Budget Importer')
    filename = fields.Char(string='Filename')
    data = fields.Json(string='Data')
    data_text = fields.Text(string='Data (Text)', compute='_compute_data_text')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='State', default='pending')
    message = fields.Text(string='Message')

    @api.depends('data')
    def _compute_data_text(self):
        for record in self:
            record.data_text = json.dumps(record.data, indent=4) if record.data else ''