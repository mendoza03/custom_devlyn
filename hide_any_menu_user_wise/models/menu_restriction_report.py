# -*- coding: utf-8 -*-
from odoo import fields, models


class MenuRestrictionReport(models.Model):
    _name = "menu.restriction.report"
    _description = "Menu Restriction Hidden Report"
    _order = "restriction_group_id, report_id"

    restriction_group_id = fields.Many2one(
        "menu.restriction.group",
        string="Restriction Group",
        required=True,
        ondelete="cascade",
    )
    report_id = fields.Many2one(
        "ir.actions.report",
        string="Report",
        required=True,
        ondelete="cascade",
    )
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        (
            "unique_group_report",
            "UNIQUE(restriction_group_id, report_id)",
            "This report is already configured for this group!",
        )
    ]