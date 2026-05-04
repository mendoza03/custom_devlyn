# -*- coding: utf-8 -*-

from odoo import models

import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------

    def _convert_opportunity_data(self, customer, team_id=False):
        res = super()._convert_opportunity_data(customer, team_id)
        if self._context.get('assignment_leads', False):
            res.pop('type')
        return res