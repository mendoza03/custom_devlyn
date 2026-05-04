# -*- coding: utf-8 -*-

from odoo import fields, models

import logging

_logger = logging.getLogger(__name__)


class CrmTeamMemberPercentage(models.Model):
    _name = 'crm.team.member.percentage'
    _description = 'CRM Team Member Percentage'

    crm_team_id = fields.Many2one('crm.team', string='CRM Team', required=True, ondelete='cascade', copy=False)
    name = fields.Char(related='member_id.name', store=True)
    member_id = fields.Many2one('crm.team.member', string='Member', required=True)
    percentage = fields.Float(string='Percentage', required=True)