# -*- coding: utf-8 -*-
from odoo import models, fields

class MailActivityScheduleCcima(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    task_time = fields.Datetime(string='Time when the task was completed')

    #! ---------------------------------------------------------
    #! OVERWRITTEN METHODS
    #! ---------------------------------------------------------

    def _action_schedule_activities(self) -> models.Model:
        return self._get_applied_on_records().activity_schedule(
            activity_type_id=self.activity_type_id.id,
            automated=False,
            summary=self.summary,
            note=self.note,
            user_id=self.activity_user_id.id,
            date_deadline=self.date_deadline,
            task_time=self.task_time
        )
