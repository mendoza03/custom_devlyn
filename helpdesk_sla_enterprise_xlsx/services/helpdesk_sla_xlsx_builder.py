# -*- coding: utf-8 -*-

import base64
from io import BytesIO

from odoo import _, fields, models
from odoo.exceptions import UserError


class HelpdeskSLAXlsxBuilder(models.AbstractModel):
    _name = "helpdesk.sla.xlsx.builder"
    _description = "Helpdesk SLA XLSX Builder"

    def build(self, wizard, payload):
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_("The Python package 'xlsxwriter' is required to export this report."))

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        formats = self._get_formats(workbook)
        self._write_executive_summary(workbook, formats, wizard, payload)
        self._write_details(workbook, formats, wizard, payload["rows"])
        self._write_summary_sheet(workbook, formats, "Team Summary", payload["team_summary"])
        self._write_summary_sheet(workbook, formats, "Agent Summary", payload["agent_summary"])
        self._write_summary_sheet(workbook, formats, "Monthly Summary", payload["month_summary"])

        workbook.close()
        output.seek(0)

        filename = "helpdesk_sla_enterprise_%s_%s.xlsx" % (wizard.date_from, wizard.date_to)
        attachment = self.env["ir.attachment"].sudo().create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(output.read()),
            "res_model": wizard._name,
            "res_id": wizard.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def _get_formats(self, workbook):
        return {
            "title": workbook.add_format({
                "bold": True,
                "font_size": 18,
                "font_color": "#1F4E78",
            }),
            "subtitle": workbook.add_format({
                "bold": True,
                "font_size": 11,
                "font_color": "#666666",
            }),
            "section": workbook.add_format({
                "bold": True,
                "font_size": 12,
                "bg_color": "#D9EAF7",
                "border": 1,
            }),
            "header": workbook.add_format({
                "bold": True,
                "font_color": "white",
                "bg_color": "#1F4E78",
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }),
            "text": workbook.add_format({"border": 1, "valign": "top"}),
            "date": workbook.add_format({"border": 1, "num_format": "yyyy-mm-dd hh:mm", "valign": "top"}),
            "number": workbook.add_format({"border": 1, "num_format": "0.00", "valign": "top"}),
            "percent": workbook.add_format({"border": 1, "num_format": "0.00%", "valign": "top"}),
            "ok": workbook.add_format({"border": 1, "bg_color": "#C6EFCE", "font_color": "#006100", "bold": True}),
            "fail": workbook.add_format({"border": 1, "bg_color": "#FFC7CE", "font_color": "#9C0006", "bold": True}),
            "neutral": workbook.add_format({"border": 1, "bg_color": "#F2F2F2"}),
            "kpi_label": workbook.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1}),
            "kpi_value": workbook.add_format({"bold": True, "font_size": 12, "border": 1, "align": "center"}),
        }

    def _write_executive_summary(self, workbook, formats, wizard, payload):
        ws = workbook.add_worksheet("Executive Summary")
        summary = payload["summary"]

        ws.write(0, 0, "Helpdesk SLA Report", formats["title"])
        ws.write(1, 0, "Generated for: %s" % (wizard.company_id.display_name or ""), formats["subtitle"])
        ws.write(2, 0, "Period: %s to %s" % (wizard.date_from, wizard.date_to), formats["subtitle"])

        kpis = [
            ("Total Closed Tickets", summary["total"]),
            ("SLA Met", summary["met"]),
            ("SLA Breached", summary["breached"]),
            ("SLA Compliance %", summary["compliance"]),
            ("Tickets With Native SLA", summary["with_sla"]),
            ("Tickets Without Native SLA", summary["without_sla"]),
            ("Avg Resolution Hours", summary["avg_resolution"]),
            ("Avg First Response Hours", summary["avg_first_response"]),
        ]

        row = 5
        ws.write(row, 0, "KPI", formats["header"])
        ws.write(row, 1, "Value", formats["header"])
        for label, value in kpis:
            row += 1
            ws.write(row, 0, label, formats["kpi_label"])
            ws.write(row, 1, value, formats["kpi_value"])

        ws.write(5, 3, "Applied Filters", formats["header"])
        filters = [
            ("Teams", ", ".join(wizard.team_ids.mapped("display_name")) or "All"),
            ("Assigned Users", ", ".join(wizard.user_ids.mapped("display_name")) or "All"),
            ("Breached Only", "Yes" if wizard.breached_only else "No"),
            ("Include Open Tickets", "Yes" if wizard.include_open_tickets else "No"),
            ("Include Tickets Without SLA", "Yes" if wizard.include_no_sla else "No"),
            ("Fallback SLA Target Hours", wizard.sla_target_hours),
        ]

        frow = 6
        for label, value in filters:
            ws.write(frow, 3, label, formats["kpi_label"])
            ws.write(frow, 4, value, formats["text"])
            frow += 1

        ws.set_column(0, 0, 28)
        ws.set_column(1, 1, 18)
        ws.set_column(3, 3, 28)
        ws.set_column(4, 4, 45)

    def _write_details(self, workbook, formats, wizard, rows):
        ws = workbook.add_worksheet("SLA Details")

        headers = [
            "Ticket",
            "Reference",
            "Team",
            "Agent",
            "Customer",
            "Stage",
            "Category",
            "Subcategory",
            "Created Date",
            "Closed Date",
            "First Response Date",
            "Nearest SLA Deadline",
            "First Response Hours",
            "Resolution Hours",
            "Native SLA Policies",
            "Failed SLA Policies",
            "Successful SLA Policies",
            "SLA Status",
            "Audit Source",
        ]

        for col, header in enumerate(headers):
            ws.write(0, col, header, formats["header"])

        for row_idx, row in enumerate(rows, start=1):
            values = [
                row["ticket"],
                row["reference"],
                row["team"],
                row["agent"],
                row["customer"],
                row["stage"],
                row["category"],
                row["subcategory"],
                row["created_date"],
                row["closed_date"],
                row["first_response_date"],
                row["sla_deadline"],
                row["first_response_hours"],
                row["resolution_hours"],
                row["sla_policy_count"],
                row["sla_failed_count"],
                row["sla_success_count"],
                "MET" if row["sla_met"] else "BREACHED",
                row["audit_source"],
            ]

            for col, value in enumerate(values):
                if col in (8, 9, 10, 11):
                    self._write_datetime(ws, row_idx, col, value, formats, wizard)
                elif col in (12, 13):
                    ws.write_number(row_idx, col, float(value or 0), formats["number"])
                elif col in (14, 15, 16):
                    ws.write_number(row_idx, col, int(value or 0), formats["text"])
                elif col == 17:
                    ws.write(row_idx, col, value, formats["ok"] if value == "MET" else formats["fail"])
                else:
                    ws.write(row_idx, col, value or "", formats["text"])

        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, max(len(rows), 1), len(headers) - 1)
        widths = [32, 16, 22, 22, 28, 18, 22, 22, 18, 18, 18, 18, 16, 16, 16, 16, 18, 14, 18]
        for col, width in enumerate(widths):
            ws.set_column(col, col, width)

    def _write_summary_sheet(self, workbook, formats, title, rows):
        ws = workbook.add_worksheet(title[:31])
        headers = [
            title.replace(" Summary", ""),
            "Total Tickets",
            "SLA Met",
            "SLA Breached",
            "SLA Compliance %",
            "Tickets With Native SLA",
            "Tickets Without Native SLA",
            "Avg Resolution Hours",
            "Avg First Response Hours",
        ]

        for col, header in enumerate(headers):
            ws.write(0, col, header, formats["header"])

        for row_idx, row in enumerate(rows, start=1):
            values = [
                row["name"],
                row["total"],
                row["met"],
                row["breached"],
                (row["compliance"] or 0) / 100.0,
                row["with_sla"],
                row["without_sla"],
                row["avg_resolution"],
                row["avg_first_response"],
            ]

            for col, value in enumerate(values):
                if col == 4:
                    ws.write_number(row_idx, col, float(value or 0), formats["percent"])
                elif col in (1, 2, 3, 5, 6):
                    ws.write_number(row_idx, col, int(value or 0), formats["text"])
                elif col in (7, 8):
                    ws.write_number(row_idx, col, float(value or 0), formats["number"])
                else:
                    ws.write(row_idx, col, value or "", formats["text"])

        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, max(len(rows), 1), len(headers) - 1)
        ws.set_column(0, 0, 30)
        ws.set_column(1, len(headers) - 1, 20)

    def _write_datetime(self, ws, row, col, value, formats, wizard):
        if not value:
            ws.write(row, col, "", formats["text"])
            return
        local_dt = fields.Datetime.context_timestamp(wizard, value).replace(tzinfo=None)
        ws.write_datetime(row, col, local_dt, formats["date"])
