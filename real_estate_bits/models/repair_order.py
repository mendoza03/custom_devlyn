# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class Repair(models.Model):
    _inherit = 'repair.order'

    project_id = fields.Many2one('project.worksite', 'Worksite / Project', copy=False)
    is_maintenance = fields.Boolean(default=False)
