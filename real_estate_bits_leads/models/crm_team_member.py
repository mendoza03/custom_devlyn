# -*- coding: utf-8 -*-

from odoo import api, models

import logging

_logger = logging.getLogger(__name__)


class CrmTeamMember(models.Model):
    _inherit = 'crm.team.member'

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, values_list):
        res = super().create(values_list)
        for record in res:
            campaigns_available = record.crm_team_id.campaign_ids.filtered(lambda campaign: not campaign.restricted)
            if campaigns_available:
                for campaign in campaigns_available:
                    campaign.write({'crm_team_member_ids': [(4, record.id)]})
        return res

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------

    def _get_assignment_quota(self, force_quota=False):
        assignment_max = self._context.get('assignment_max', False)
        return assignment_max if assignment_max else super()._get_assignment_quota(force_quota)

    # -------------------------------------------------------------------------
    # HELPERS METHODS
    # -------------------------------------------------------------------------

    def _get_assignment_max(self):
        if self.crm_team_id.type == 'average':
            return 10000 / len(self.crm_team_id.crm_team_member_ids.filtered(lambda member: not member.assignment_optout))
        elif self.crm_team_id.type == 'percentage':
            percentage = self.crm_team_id.assign_percentage_ids.filtered(lambda percentage: percentage.member_id and percentage.member_id == self)
            _logger.info(percentage)
            if percentage:
                return 10000 * (percentage[0].percentage / 100)
            else:
                return 0
        else:
            return self.assignment_max