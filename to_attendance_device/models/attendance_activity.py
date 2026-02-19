from odoo import models, fields, api


class AttendanceActivity(models.Model):
    _name = 'attendance.activity'
    _description = 'Attendance Activity'

    name = fields.Char(string='Name', required=True, translate=True,
                              help="The name of the attendance activity. E.g. Normal Working, Overtime, etc")

    attendance_status_ids = fields.One2many('attendance.state', 'activity_id', string='Attendance Status',
                                            help="The check-in and check-out statuses of this activity")

    status_count = fields.Integer(string='Status Count', compute='_compute_status_count')

    _unique_name = models.Constraint(
        'unique(name)',
        "The Name of the attendance activity must be unique!",
    )

    @api.depends('attendance_status_ids')
    def _compute_status_count(self):
        data = self.env['attendance.state']._read_group(
            [('activity_id', 'in', self.ids)], ['activity_id'], ['__count'])
        mapped_data = {activity.id: count for activity, count in data}
        for r in self:
            r.status_count = mapped_data.get(r.id, 0)

    def getAttendance(self, device_id=None, user_id=None):
        domain = [('attendance_state_id', 'in', self.attendance_status_ids.ids)]
        if device_id:
            domain += [('device_id', '=', device_id.id)]

        if user_id:
            domain += [('user_id', '=', user_id.id)]

        return self.env['user.attendance'].search(domain)
