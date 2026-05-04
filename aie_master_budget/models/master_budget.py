# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from itertools import groupby
from operator import itemgetter
from ..tools.logger_config import configure_logger

_logger = configure_logger()


class BudgetMaster(models.Model):
    _name = 'master.budget'
    _description = 'Master Budget'

    name = fields.Char(string='Name', help='Budget name', required=True, readonly=True, copy=False, default=lambda self: _('New'))
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
    ], string='State', default='draft')
    project_id = fields.Many2one(comodel_name='project.project', string='Project')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', required=True, default=lambda self: self.env.company)
    period_start = fields.Date(string='Period Start')
    period_end = fields.Date(string='Period End')
    line_ids = fields.One2many(comodel_name='master.budget.line', inverse_name='budget_id', string='budget lines', copy=True, auto_join=True)

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['project.project'].browse(vals['project_id']).name
        return super().create(vals_list)

    def write(self, values):
        if 'project_id' in values:
            values['name'] = self.env['project.project'].browse(values['project_id']).name
        return super().write(values)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def action_confirm(self):
        for record in self:
            record.write({
                'state': 'confirm',
            })