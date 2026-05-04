# -*- coding: utf-8 -*-

from datetime import date, datetime, time

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelpdeskSLAReportWizard(models.TransientModel):
    _name = "helpdesk.sla.report.wizard"
    _description = "Helpdesk SLA Report Wizard"

    name = fields.Char(default="SLA Report")
    date_from = fields.Date(
        string="Date From",
        required=True,
        default=lambda self: date.today().replace(day=1),
    )
    date_to = fields.Date(
        string="Date To",
        required=True,
        default=fields.Date.context_today,
    )

    team_ids = fields.Many2many(
        "helpdesk.team",
        "helpdesk_sla_report_wizard_team_rel",
        "wizard_id",
        "team_id",
        string="Teams",
    )
    user_ids = fields.Many2many(
        "res.users",
        "helpdesk_sla_report_wizard_user_rel",
        "wizard_id",
        "user_id",
        string="Assigned Users",
    )

    include_open_tickets = fields.Boolean(string="Include Open Tickets")
    breached_only = fields.Boolean(string="Breached Only")
    include_first_response = fields.Boolean(string="Include First Response Metrics", default=True)
    include_no_sla = fields.Boolean(string="Include Tickets Without SLA", default=True)

    sla_target_hours = fields.Float(
        string="Fallback SLA Target Hours",
        default=24.0,
        help="Used only when the ticket does not have native Odoo SLA status information.",
    )

    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )

    def _validate_dates(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("Date From cannot be greater than Date To."))
        if self.sla_target_hours <= 0:
            raise UserError(_("Fallback SLA Target Hours must be greater than zero."))

    def action_export_xlsx(self):
        self.ensure_one()
        self._validate_dates()
        return self.env["helpdesk.sla.report.service"].export_xlsx(self)
