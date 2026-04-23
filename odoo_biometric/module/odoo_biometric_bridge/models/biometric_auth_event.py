import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class BiometricAuthEvent(models.Model):
    _name = "biometric.auth.event"
    _description = "Biometric Authentication Event"
    _order = "create_date desc"

    name = fields.Char(default=lambda self: _("Biometric Event"), required=True)
    event_type = fields.Selection(
        [("login", "Login"), ("logout", "Logout")], required=True, index=True
    )
    result = fields.Selection(
        [("success", "Success"), ("failed", "Failed")], required=True, index=True
    )
    reason = fields.Char()

    flow_mode = fields.Char()
    auth_channel = fields.Char(default="standard", index=True)

    login = fields.Char(index=True)
    user_id = fields.Many2one("res.users", index=True)

    attendance_action = fields.Selection(
        [("check_in", "Check In"), ("check_out", "Check Out")]
    )
    attendance_status = fields.Selection(
        [
            ("success", "Success"),
            ("failed", "Failed"),
            ("skipped", "Skipped"),
        ],
        default="skipped",
        index=True,
    )
    attendance_id = fields.Many2one("hr.attendance", index=True)

    auto_close_applied = fields.Boolean(default=False)
    auto_close_reason = fields.Char()
    auto_closed_attendance_id = fields.Many2one("hr.attendance")

    ip_public = fields.Char()
    x_forwarded_for = fields.Char()
    user_agent = fields.Text()
    browser = fields.Char()
    os = fields.Char()
    device_type = fields.Char()

    lat = fields.Float()
    lon = fields.Float()
    accuracy = fields.Float()

    country = fields.Char()
    city = fields.Char()
    asn = fields.Char()
    isp = fields.Char()

    network_type = fields.Char()
    downlink = fields.Float()
    rtt = fields.Float()

    liveness_provider = fields.Char()
    liveness_passed = fields.Boolean()
    liveness_score = fields.Float()
    rekognition_session_id = fields.Char(index=True)
    s3_video_url = fields.Char()
    cognito_sub = fields.Char(index=True)

    face_match_attempted = fields.Boolean(default=False)
    face_match_passed = fields.Boolean(default=False)
    face_match_similarity = fields.Float()
    face_match_reason = fields.Char()
    face_match_request_id = fields.Char(index=True)

    raw_payload = fields.Json(default=dict)

    alert_ids = fields.One2many("biometric.auth.alert", "event_id")

    @api.model
    def create_from_gateway(self, payload):
        telemetry = payload.get("telemetry") or {}
        login = payload.get("login")
        user = self.env["res.users"].sudo().search([("login", "=", login)], limit=1) if login else False

        vals = {
            "name": f"{payload.get('event_type', 'event').title()} - {login or 'unknown'}",
            "event_type": payload.get("event_type") or "login",
            "result": payload.get("result") or "failed",
            "reason": payload.get("reason"),
            "flow_mode": payload.get("flow_mode"),
            "auth_channel": payload.get("auth_channel") or "standard",
            "login": login,
            "user_id": user.id if user else False,
            "attendance_action": payload.get("attendance_action"),
            "attendance_status": payload.get("attendance_status") or "skipped",
            "ip_public": telemetry.get("ip_public"),
            "x_forwarded_for": telemetry.get("x_forwarded_for"),
            "user_agent": telemetry.get("user_agent"),
            "browser": telemetry.get("browser"),
            "os": telemetry.get("os"),
            "device_type": telemetry.get("device_type"),
            "lat": telemetry.get("lat"),
            "lon": telemetry.get("lon"),
            "accuracy": telemetry.get("accuracy"),
            "country": telemetry.get("country"),
            "city": telemetry.get("city"),
            "asn": telemetry.get("asn"),
            "isp": telemetry.get("isp"),
            "network_type": telemetry.get("network_type"),
            "downlink": telemetry.get("downlink"),
            "rtt": telemetry.get("rtt"),
            "liveness_provider": payload.get("liveness_provider"),
            "liveness_passed": payload.get("liveness_passed"),
            "liveness_score": payload.get("liveness_score"),
            "rekognition_session_id": payload.get("rekognition_session_id"),
            "s3_video_url": payload.get("s3_video_url"),
            "cognito_sub": payload.get("cognito_sub"),
            "face_match_attempted": bool(payload.get("face_match_attempted")),
            "face_match_passed": bool(payload.get("face_match_passed")),
            "face_match_similarity": payload.get("face_match_similarity"),
            "face_match_reason": payload.get("face_match_reason"),
            "face_match_request_id": payload.get("face_match_request_id"),
            "raw_payload": payload.get("raw_payload") or {},
        }

        event = self.sudo().create(vals)
        attendance_error = event._process_attendance(payload, user)
        event._process_alerts()
        return event, attendance_error

    def _process_attendance(self, payload, user):
        self.ensure_one()
        policy = self.env["biometric.policy"].sudo().get_active_policy()

        if not policy.attendance_sync_enabled:
            self.attendance_status = "skipped"
            return None

        action = payload.get("attendance_action")
        if action not in {"check_in", "check_out"}:
            self.attendance_status = "skipped"
            return None

        if not user:
            self.attendance_status = "failed"
            self.result = "failed"
            self.reason = "user_not_found"
            return {
                "error": "user_not_found",
                "message": _("Login is not mapped to any Odoo user."),
            }

        employee = self.env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)
        if not employee and user.login == "admin":
            employee = self._ensure_admin_employee(user)
        if not employee:
            self.attendance_status = "failed"
            self.result = "failed"
            self.reason = "employee_not_linked"
            return {
                "error": "employee_not_linked",
                "message": _("User has no linked employee in Odoo."),
            }

        telemetry = payload.get("telemetry") or {}
        auto_closed = self._auto_close_previous_day_open_attendance(employee, telemetry)
        if auto_closed:
            self.auto_close_applied = True
            self.auto_close_reason = "previous_day_open_attendance"
            self.auto_closed_attendance_id = auto_closed.id

        open_attendance = self.env["hr.attendance"].sudo().search(
            [("employee_id", "=", employee.id), ("check_out", "=", False)],
            order="check_in desc",
            limit=1,
        )

        now_dt = fields.Datetime.now()
        if action == "check_in":
            if open_attendance:
                self.attendance_status = "failed"
                self.result = "failed"
                self.reason = "attendance_open_exists"
                return {
                    "error": "attendance_open_exists",
                    "message": _("Cannot mark check in while another attendance is still open."),
                }

            attendance_vals = self._build_check_in_vals(employee, now_dt, telemetry)
            attendance = self.env["hr.attendance"].sudo().create(attendance_vals)
            self.attendance_status = "success"
            self.attendance_id = attendance.id
            return None

        if not open_attendance:
            self.attendance_status = "failed"
            self.result = "failed"
            self.reason = "attendance_open_missing"
            return {
                "error": "attendance_open_missing",
                "message": _("Cannot mark check out without an open attendance."),
            }

        open_attendance.sudo().write(self._build_check_out_vals(now_dt, telemetry, "manual"))
        self.attendance_status = "success"
        self.attendance_id = open_attendance.id
        return None

    def _ensure_admin_employee(self, user):
        employee_model = self.env["hr.employee"].sudo()
        employee = employee_model.search([("user_id", "=", user.id)], limit=1)
        if employee:
            return employee

        vals = {
            "name": (getattr(user.partner_id, "name", False) or user.login or "Admin"),
            "user_id": user.id,
            "company_id": user.company_id.id if user.company_id else False,
        }
        try:
            employee = employee_model.create(vals)
            _logger.info("Created admin employee link user_id=%s employee_id=%s", user.id, employee.id)
            return employee
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Could not auto-create admin employee for user_id=%s: %s", user.id, exc)
            return False

    def _auto_close_previous_day_open_attendance(self, employee, telemetry):
        open_attendance = self.env["hr.attendance"].sudo().search(
            [("employee_id", "=", employee.id), ("check_out", "=", False)],
            order="check_in desc",
            limit=1,
        )
        if not open_attendance or not open_attendance.check_in:
            return False

        tz = self._employee_timezone(employee)
        now_local = pytz.utc.localize(fields.Datetime.now()).astimezone(tz)
        open_local = pytz.utc.localize(open_attendance.check_in).astimezone(tz)
        if open_local.date() >= now_local.date():
            return False

        auto_close_local = datetime.combine(open_local.date(), time(hour=23, minute=59, second=59))
        auto_close_utc = tz.localize(auto_close_local).astimezone(pytz.utc).replace(tzinfo=None)
        if auto_close_utc <= open_attendance.check_in:
            auto_close_utc = open_attendance.check_in + timedelta(seconds=1)

        write_vals = self._build_check_out_vals(auto_close_utc, telemetry, "auto_check_out")
        open_attendance.sudo().write(write_vals)
        return open_attendance

    def _build_check_in_vals(self, employee, check_in, telemetry):
        return {
            "employee_id": employee.id,
            "check_in": check_in,
            "in_mode": "manual",
            "in_latitude": telemetry.get("lat"),
            "in_longitude": telemetry.get("lon"),
            "in_location": self._location_text(telemetry),
            "in_ip_address": self._ip_text(telemetry),
            "in_browser": telemetry.get("browser"),
        }

    def _build_check_out_vals(self, check_out, telemetry, out_mode):
        return {
            "check_out": check_out,
            "out_mode": out_mode,
            "out_latitude": telemetry.get("lat"),
            "out_longitude": telemetry.get("lon"),
            "out_location": self._location_text(telemetry),
            "out_ip_address": self._ip_text(telemetry),
            "out_browser": telemetry.get("browser"),
        }

    def _employee_timezone(self, employee):
        if hasattr(employee, "_get_tz"):
            try:
                tz_name = employee._get_tz()
                if tz_name:
                    return pytz.timezone(tz_name)
            except Exception:  # noqa: BLE001
                pass

        tz_name = (
            getattr(employee, "tz", False)
            or employee.company_id.resource_calendar_id.tz
            or self.env.user.tz
            or "UTC"
        )
        return pytz.timezone(tz_name)

    def _location_text(self, telemetry):
        city = (telemetry.get("city") or "").strip()
        country = (telemetry.get("country") or "").strip()
        if city and country:
            return f"{city}, {country}"
        if city:
            return city
        if country:
            return country
        return telemetry.get("ip_public") or telemetry.get("x_forwarded_for") or "Unknown"

    def _ip_text(self, telemetry):
        return telemetry.get("ip_public") or telemetry.get("x_forwarded_for")

    def _process_alerts(self):
        for event in self:
            policy = self.env["biometric.policy"].sudo().get_active_policy()

            if event.result == "failed":
                event._create_alert("high", "AUTH_FAILED", _("Authentication failed."))

            if policy.alert_low_score and event.liveness_score and event.liveness_score < policy.liveness_threshold:
                event._create_alert(
                    "medium",
                    "LOW_LIVENESS_SCORE",
                    _("Liveness score below policy threshold."),
                )

            if policy.alert_country_change and event.user_id and event.country:
                recent = self.search(
                    [
                        ("id", "!=", event.id),
                        ("user_id", "=", event.user_id.id),
                        ("country", "!=", False),
                        ("result", "=", "success"),
                    ],
                    limit=10,
                    order="id desc",
                )
                known = {r.country for r in recent if r.country}
                if known and event.country not in known:
                    event._create_alert(
                        "high",
                        "COUNTRY_ANOMALY",
                        _("Authentication from a new country for this user."),
                    )

            if policy.alert_asn_change and event.user_id and event.asn:
                recent = self.search(
                    [
                        ("id", "!=", event.id),
                        ("user_id", "=", event.user_id.id),
                        ("asn", "!=", False),
                        ("result", "=", "success"),
                    ],
                    limit=10,
                    order="id desc",
                )
                known = {r.asn for r in recent if r.asn}
                if known and event.asn not in known:
                    event._create_alert(
                        "medium",
                        "ASN_ANOMALY",
                        _("Authentication from a new ASN/ISP for this user."),
                    )

            if policy.alert_new_device and event.user_id:
                fp = self._build_device_fingerprint(event)
                device = self.env["biometric.device"].sudo().search(
                    [
                        ("user_id", "=", event.user_id.id),
                        ("device_fingerprint", "=", fp),
                    ],
                    limit=1,
                )
                if device:
                    device.last_seen = fields.Datetime.now()
                else:
                    self.env["biometric.device"].sudo().create(
                        {
                            "user_id": event.user_id.id,
                            "device_fingerprint": fp,
                            "browser": event.browser,
                            "os": event.os,
                            "device_type": event.device_type or "other",
                        }
                    )
                    event._create_alert(
                        "medium",
                        "NEW_DEVICE",
                        _("Authentication from a new device fingerprint."),
                    )

    def _build_device_fingerprint(self, event):
        parts = [
            event.browser or "",
            event.os or "",
            event.device_type or "",
            event.user_agent or "",
        ]
        return "|".join(parts)[:255]

    def _create_alert(self, severity, code, message):
        self.env["biometric.auth.alert"].sudo().create(
            {
                "name": f"{code} - {self.login or 'unknown'}",
                "event_id": self.id,
                "user_id": self.user_id.id,
                "severity": severity,
                "code": code,
                "message": message,
            }
        )
        if self.auth_channel != "admin_demo":
            self._notify_admins(code, severity, message)

    def _notify_admins(self, code, severity, message):
        admin_group = self.env.ref("base.group_system", raise_if_not_found=False)
        if not admin_group:
            return
        admins = getattr(admin_group, "user_ids", False) or getattr(admin_group, "users", False)
        recipients = [u.partner_id.email for u in admins if u.partner_id.email]
        if not recipients:
            return
        mail_values = {
            "subject": f"[Biometric Alert] {code} ({severity})",
            "body_html": f"<p>{message}</p><p>Usuario: {self.login or 'N/A'}</p>",
            "email_to": ",".join(recipients),
        }
        try:
            self.env["mail.mail"].sudo().create(mail_values).send()
        except Exception as exc:  # noqa: BLE001
            _logger.warning("Could not send biometric alert email: %s", exc)
