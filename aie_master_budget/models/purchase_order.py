# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    budget_id = fields.Many2one(comodel_name='master.budget', string='Budget', compute='_compute_budget_id')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('project_id')
    def _compute_budget_id(self):
        for record in self:
            if record.project_id:
                project_id = self.env['master.budget'].search([('project_id', '=', record.project_id.id)], limit=1)
                record.budget_id = project_id.id if project_id else False
            else:
                record.budget_id = False

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for record in self:
            for line in record.order_line:
                line.task_id = False
                line.concept_id = False
                line.budget_item_id = False