# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Team(models.Model):
    _inherit = 'crm.team'

    @api.depends()
    def _compute_is_apply(self):
        for rec in self:
            commission_based_on = rec.company_id.commission_based_on if rec.company_id else self.env.company.commission_based_on
            rec.is_apply = False
            if commission_based_on == 'sales_team':
                rec.is_apply = True

    commission_type = fields.Selection(string="Commission Amount Type",
                                       selection=[('percentage', 'By Percentage'), ('fix', 'Fixed Amount')])
    is_apply = fields.Boolean(string='Is Apply ?', compute='_compute_is_apply')
    commission_range_ids = fields.One2many('sales.commission.range', 'commission_team_id',
                                           string='Sales Commission Range')
