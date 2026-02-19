from odoo import models, fields, _
from odoo.exceptions import UserError


class DeviceConfirmWizard(models.TransientModel):
    _name = 'device.confirm.wizard'
    _description = 'Machine Confirm Wizard'

    def _default_attendance_device(self):
        if self.env.context.get('employee_upload_wizard_id'):
            return False
        return self.env.context.get('active_id')

    def _default_title(self):
        return self.env.context.get('title')

    def _default_content(self):
        return self.env.context.get('content') or self.env.context.get('confirm')

    def _default_safe_confirm(self):
        return self.env.context.get('safe_confirm')

    def _default_employee_upload_wizard_id(self):
        return self.env.context.get('employee_upload_wizard_id')

    device_id = fields.Many2one('attendance.device', default=_default_attendance_device)
    title = fields.Char(string='Title of confirmation', default=_default_title)
    content = fields.Text(string='Confirmation content', default=_default_content)
    safe_confirm = fields.Boolean(string='Safety To Confirm', default=_default_safe_confirm)
    safe_checked = fields.Boolean(string='Safe Checked', default=False)
    employee_upload_wizard_id = fields.Many2one('employee.upload.wizard', default=_default_employee_upload_wizard_id)

    def ok(self):
        ctx_method = self.env.context.get('method', False)
        if ctx_method in (
            '_user_download',
            '_employee_map',
            '_finger_template_download',
            '_user_upload',
            '_attendance_clear',
            '_restart',
            '_icloud_download_users',
            '_icloud_download_fingers',
            'action_employee_upload',
            ):

            if ctx_method in (
                '_attendance_clear',
                ) and not self.safe_checked:
                raise UserError(_("You must check the commitment \"I am sure about this.\" first!"))
            if self.device_id:
                getattr(self.device_id, ctx_method)()
            else:
                getattr(self.employee_upload_wizard_id, ctx_method)()
