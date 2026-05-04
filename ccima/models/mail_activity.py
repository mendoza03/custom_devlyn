# -*- coding: utf-8 -*-
import pytz

from odoo import fields, models, api, _


class MailActivityCcima(models.Model):
    _inherit = 'mail.activity'

    task_time = fields.Datetime(string='Time when the task was completed')
    
    #* ---------------------------------------------------------
    #*  SUPER METHODS
    #* ---------------------------------------------------------
    
    def _action_done(self, feedback=False, attachment_ids=None):
        time_task_value = self.task_time if self.task_time else fields.Datetime.now().astimezone(pytz.timezone(self.user_id.tz))
        task_base_message = _("End date and time")
        task_final_message =  f"{task_base_message}: {time_task_value}"
        feedback = feedback + f"\n{task_final_message}" if feedback else f"{task_final_message}" 
        messages, next_activities = super(MailActivityCcima, self)._action_done(feedback=feedback,  attachment_ids=None)
        return messages, next_activities
    
