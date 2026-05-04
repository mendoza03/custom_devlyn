# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    @api.model
    def get_bindings(self, model_name):
        result = super().get_bindings(model_name)

        if self.env.su or self.env.user.has_group("base.group_system"):
            return result

        try:
            hidden_reports = self.env["menu.restriction.report"].sudo().search([
                ("active", "=", True),
            ])
            if not hidden_reports:
                return result

            user_id = self.env.user.id
            hidden_report_ids = set()
            for hr in hidden_reports:
                group = hr.restriction_group_id
                if not group.active:
                    continue
                if user_id in group.user_ids.ids:
                    hidden_report_ids.add(hr.report_id.id)

            if not hidden_report_ids:
                return result

            if "report" in result:
                result["report"] = [
                    r for r in result["report"]
                    if r.get("id") not in hidden_report_ids
                ]

        except Exception as e:
            _logger.error("MENU RESTRICTION REPORT ERROR: model=%s error=%s", model_name, str(e))

        return result