from odoo import api, models

from ..services.report_utils import to_local_datetime


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    def _devlyn_journey_rebuild_is_disabled(self) -> bool:
        return bool(self.env.context.get("skip_devlyn_journey_rebuild"))

    def _devlyn_journey_relevant_fields(self) -> set[str]:
        return {
            "employee_id",
            "check_in",
            "check_out",
            "worked_hours",
            "biometric_source",
            "biometric_auto_closed",
            "biometric_auto_close_reason",
            "biometric_checkin_event_id",
            "biometric_checkout_event_id",
        }

    def _devlyn_journey_key_pairs(self) -> set[tuple[int, object]]:
        if not self:
            return set()
        tz_name = self.env["devlyn.attendance.journey.service"].get_timezone_name()
        pairs: set[tuple[int, object]] = set()
        for record in self:
            if record.biometric_source != "biometric_v1":
                continue
            if not record.employee_id or not record.check_in:
                continue
            local_check_in = to_local_datetime(record.check_in, tz_name)
            if not local_check_in:
                continue
            pairs.add((record.employee_id.id, local_check_in.date()))
        return pairs

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if records and not records._devlyn_journey_rebuild_is_disabled():
            self.env["devlyn.attendance.journey.service"].rebuild_key_pairs(records._devlyn_journey_key_pairs())
        return records

    def write(self, vals):
        should_rebuild = bool(set(vals).intersection(self._devlyn_journey_relevant_fields()))
        before_pairs = self._devlyn_journey_key_pairs() if should_rebuild else set()
        result = super().write(vals)
        if should_rebuild and not self._devlyn_journey_rebuild_is_disabled():
            after_pairs = self._devlyn_journey_key_pairs()
            self.env["devlyn.attendance.journey.service"].rebuild_key_pairs(before_pairs | after_pairs)
        return result

    def unlink(self):
        pairs = self._devlyn_journey_key_pairs()
        result = super().unlink()
        if pairs and not self._devlyn_journey_rebuild_is_disabled():
            self.env["devlyn.attendance.journey.service"].rebuild_key_pairs(pairs)
        return result
