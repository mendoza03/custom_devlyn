# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, time

from odoo import api, fields, models


class HelpdeskSLAReportService(models.AbstractModel):
    _name = "helpdesk.sla.report.service"
    _description = "Helpdesk SLA Report Service"

    def export_xlsx(self, wizard):
        payload = self._prepare_report_payload(wizard)
        return self.env["helpdesk.sla.xlsx.builder"].build(wizard, payload)

    def _prepare_report_payload(self, wizard):
        tickets = self._get_tickets(wizard)
        sla_map = self._get_sla_map(tickets)
        first_response_map = self._get_first_response_map(tickets) if wizard.include_first_response else {}

        rows = []
        for ticket in tickets:
            row = self._prepare_ticket_row(wizard, ticket, sla_map.get(ticket.id, {}), first_response_map.get(ticket.id))
            if wizard.breached_only and not row["sla_breached"]:
                continue
            if not wizard.include_no_sla and not row["has_sla"]:
                continue
            rows.append(row)

        return {
            "rows": rows,
            "summary": self._build_summary(rows),
            "team_summary": self._build_group_summary(rows, "team"),
            "agent_summary": self._build_group_summary(rows, "agent"),
            "month_summary": self._build_group_summary(rows, "closed_month"),
        }

    def _get_closed_field_name(self):
        Ticket = self.env["helpdesk.ticket"]
        for field_name in ("close_date", "closed_date", "date_closed", "date_close"):
            if field_name in Ticket._fields:
                return field_name
        return None

    def _get_domain(self, wizard):
        closed_field = self._get_closed_field_name()
        date_from_dt = datetime.combine(wizard.date_from, time.min)
        date_to_dt = datetime.combine(wizard.date_to, time.max)

        domain = []
        if closed_field and not wizard.include_open_tickets:
            domain += [
                (closed_field, ">=", fields.Datetime.to_string(date_from_dt)),
                (closed_field, "<=", fields.Datetime.to_string(date_to_dt)),
            ]
        elif closed_field and wizard.include_open_tickets:
            domain += [
                "|",
                "&",
                (closed_field, ">=", fields.Datetime.to_string(date_from_dt)),
                (closed_field, "<=", fields.Datetime.to_string(date_to_dt)),
                (closed_field, "=", False),
            ]
        else:
            domain += [
                ("write_date", ">=", fields.Datetime.to_string(date_from_dt)),
                ("write_date", "<=", fields.Datetime.to_string(date_to_dt)),
            ]

        if wizard.team_ids and "team_id" in self.env["helpdesk.ticket"]._fields:
            domain.append(("team_id", "in", wizard.team_ids.ids))
        if wizard.user_ids and "user_id" in self.env["helpdesk.ticket"]._fields:
            domain.append(("user_id", "in", wizard.user_ids.ids))

        return domain

    def _get_tickets(self, wizard):
        return self.env["helpdesk.ticket"].search(self._get_domain(wizard), order="create_date asc")

    def _get_sla_map(self, tickets):
        if not tickets:
            return {}

        if "helpdesk.sla.status" not in self.env:
            return {}

        SLAStatus = self.env["helpdesk.sla.status"]
        if "ticket_id" not in SLAStatus._fields:
            return {}

        statuses = SLAStatus.search([("ticket_id", "in", tickets.ids)])
        result = defaultdict(lambda: {
            "policy_count": 0,
            "failed_count": 0,
            "success_count": 0,
            "nearest_deadline": False,
        })

        for status in statuses:
            ticket_id = status.ticket_id.id
            result[ticket_id]["policy_count"] += 1

            deadline = self._get_first_available_value(status, ["deadline", "date_deadline"])
            reached = self._get_first_available_value(status, ["reached_datetime", "reached_date", "date_reached"])
            state = self._get_first_available_value(status, ["status", "state"])

            if deadline and (not result[ticket_id]["nearest_deadline"] or deadline < result[ticket_id]["nearest_deadline"]):
                result[ticket_id]["nearest_deadline"] = deadline

            is_failed = False
            is_success = False

            if state:
                is_failed = state == "failed"
                is_success = state in ("reached", "success", "done")
            elif deadline and reached:
                is_failed = reached > deadline
                is_success = reached <= deadline
            elif deadline and status.ticket_id:
                closed_dt = self._get_ticket_closed_datetime(status.ticket_id)
                if closed_dt:
                    is_failed = closed_dt > deadline
                    is_success = closed_dt <= deadline

            if is_failed:
                result[ticket_id]["failed_count"] += 1
            if is_success:
                result[ticket_id]["success_count"] += 1

        return dict(result)

    def _get_first_response_map(self, tickets):
        if not tickets:
            return {}

        MailMessage = self.env["mail.message"].sudo()
        domain = [
            ("model", "=", "helpdesk.ticket"),
            ("res_id", "in", tickets.ids),
            ("message_type", "=", "comment"),
            ("author_id", "!=", False),
        ]
        messages = MailMessage.search(domain, order="date asc")

        user_partner_ids = set(self.env["res.users"].sudo().search([]).mapped("partner_id").ids)
        result = {}

        for message in messages:
            if message.res_id in result:
                continue
            if message.author_id.id in user_partner_ids:
                result[message.res_id] = message.date

        return result

    def _prepare_ticket_row(self, wizard, ticket, sla_info, first_response_date):
        closed_dt = self._get_ticket_closed_datetime(ticket)
        resolution_hours = self._get_hours_between(ticket.create_date, closed_dt)
        first_response_hours = self._get_hours_between(ticket.create_date, first_response_date)

        has_sla = bool(sla_info.get("policy_count"))
        if has_sla:
            sla_breached = bool(sla_info.get("failed_count"))
            sla_met = not sla_breached
            audit_source = "Odoo SLA"
        else:
            sla_breached = bool(closed_dt and resolution_hours is not None and resolution_hours > wizard.sla_target_hours)
            sla_met = bool(closed_dt and resolution_hours is not None and resolution_hours <= wizard.sla_target_hours)
            audit_source = "Fallback Target"

        category = self._get_related_name(ticket, ["category_id", "ticket_category_id"])
        subcategory = self._get_related_name(ticket, ["subcategory_id", "ticket_subcategory_id"])
        ticket_ref = self._get_first_available_value(ticket, ["ticket_ref", "reference", "number"]) or ""

        closed_month = ""
        if closed_dt:
            closed_month = fields.Datetime.context_timestamp(wizard, closed_dt).strftime("%Y-%m")

        return {
            "ticket_id": ticket.id,
            "ticket": ticket.display_name or ticket.name or "",
            "reference": ticket_ref,
            "team": ticket.team_id.display_name if "team_id" in ticket._fields and ticket.team_id else "",
            "agent": ticket.user_id.display_name if "user_id" in ticket._fields and ticket.user_id else "",
            "customer": ticket.partner_id.display_name if "partner_id" in ticket._fields and ticket.partner_id else "",
            "stage": ticket.stage_id.display_name if "stage_id" in ticket._fields and ticket.stage_id else "",
            "category": category,
            "subcategory": subcategory,
            "created_date": ticket.create_date,
            "closed_date": closed_dt,
            "closed_month": closed_month or "Open / No Closed Date",
            "first_response_date": first_response_date,
            "first_response_hours": first_response_hours,
            "resolution_hours": resolution_hours,
            "has_sla": has_sla,
            "sla_policy_count": int(sla_info.get("policy_count") or 0),
            "sla_failed_count": int(sla_info.get("failed_count") or 0),
            "sla_success_count": int(sla_info.get("success_count") or 0),
            "sla_deadline": sla_info.get("nearest_deadline"),
            "sla_met": sla_met,
            "sla_breached": sla_breached,
            "audit_source": audit_source,
        }

    def _get_ticket_closed_datetime(self, ticket):
        for field_name in ("close_date", "closed_date", "date_closed", "date_close"):
            if field_name in ticket._fields:
                value = ticket[field_name]
                if value:
                    return value
        return False

    def _get_hours_between(self, start, end):
        if not start or not end:
            return None
        return round((end - start).total_seconds() / 3600.0, 2)

    def _get_first_available_value(self, record, field_names):
        for field_name in field_names:
            if field_name in record._fields:
                value = record[field_name]
                if value:
                    return value
        return False

    def _get_related_name(self, record, field_names):
        value = self._get_first_available_value(record, field_names)
        return value.display_name if value else ""

    def _build_summary(self, rows):
        total = len(rows)
        breached = len([row for row in rows if row["sla_breached"]])
        met = len([row for row in rows if row["sla_met"]])
        with_sla = len([row for row in rows if row["has_sla"]])
        avg_resolution = self._avg([row["resolution_hours"] for row in rows if row["resolution_hours"] is not None])
        avg_first_response = self._avg([row["first_response_hours"] for row in rows if row["first_response_hours"] is not None])

        return {
            "total": total,
            "met": met,
            "breached": breached,
            "with_sla": with_sla,
            "without_sla": total - with_sla,
            "compliance": round((met / total) * 100, 2) if total else 0.0,
            "avg_resolution": avg_resolution,
            "avg_first_response": avg_first_response,
        }

    def _build_group_summary(self, rows, key):
        grouped = defaultdict(list)
        for row in rows:
            grouped[row.get(key) or "Undefined"].append(row)

        result = []
        for group_name, group_rows in sorted(grouped.items(), key=lambda item: item[0]):
            result.append({
                "name": group_name,
                **self._build_summary(group_rows),
            })
        return result

    def _avg(self, values):
        values = list(values)
        if not values:
            return 0.0
        return round(sum(values) / len(values), 2)
