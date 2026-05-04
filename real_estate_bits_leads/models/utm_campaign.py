# -*- coding: utf-8 -*-

from odoo import fields, models

import logging

_logger = logging.getLogger(__name__)


class UtmCampaign(models.Model):
    _inherit = 'utm.campaign'

    # -------------------------------------------------------------------------
    # NEW FIELDS
    # -------------------------------------------------------------------------

    restricted = fields.Boolean(string='Restricted', default=False)
    crm_team_member_ids = fields.Many2many('crm.team.member', string='Sales Team Members', help='Add members to automatically assign their documents to this campaign.')
    crm_team_id = fields.Many2one('crm.team', string='Sales Team', help='Add a team to automatically assign their documents to this campaign.')