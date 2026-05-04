# -*- coding: utf-8 -*-

from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    master_budget_line_id = fields.Many2one(comodel_name='master.budget.line', string='Master Budget Line')
    has_admin_access_master_budget = fields.Boolean(string='Has Admin Access Master Budget', compute='_compute_has_admin_access_master_budget')

    def _compute_has_admin_access_master_budget(self):
        for record in self:
            record.has_admin_access_master_budget = self.env.user.has_group('aie_master_budget.group_access_aie_master_budget_admin')