from odoo import fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    biometric_source = fields.Char(index=True)
    biometric_inference_mode = fields.Char()
    biometric_auto_closed = fields.Boolean(default=False, index=True)
    biometric_auto_close_reason = fields.Char()
    biometric_checkin_event_id = fields.Many2one("hr.biometric.event", index=True)
    biometric_checkout_event_id = fields.Many2one("hr.biometric.event", index=True)
