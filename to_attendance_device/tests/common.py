from odoo import fields
from odoo.tests import HttpCase


class Common(HttpCase):

    def setUp(self):
        super(Common, self).setUp()
        self.attendance_activity = self.env['attendance.activity'].create({
            'name': 'test_attendance_activity'
            })
        main_partner_id = self.env.ref('base.main_partner')
        self.work_office_1 = self.env['hr.work.location'].create([
            {
                'name': "Office 1",
                'location_type': "office",
                'address_id': main_partner_id.id,
            }
        ])

        self.attendance_device_location = self.env['attendance.device.location'].create({
            'name': 'test_attendance_device_location',
            'hr_work_location_id': self.work_office_1.id,
            'tz': 'Asia/Ho_Chi_Minh',
            })
        self.hr_employee = self.env['hr.employee'].create({
            'name': 'Richard',
            'sex': 'male',
            'country_id': self.env.ref('base.be').id,
        })
        self.attendance_device = self.env['attendance.device'].create({
            'name': 'test_attendance_device',
            'ip': 'ip_test',
            'port': 4355,
            'timeout': 5,
            'password': '0',
            'location_id': self.attendance_device_location.id
            })
        self.attendance_device_user = self.env['attendance.device.user'].create({
            'name': 'test_attendance_device_user',
            'device_id': self.attendance_device.id,
            'user_id': 1,
            'employee_id': self.hr_employee.id,
            })
        self.attendance_state = self.env['attendance.state'].create({
            'name': 'test_attendance_state',
            'activity_id': self.attendance_activity.id,
            'code': 100,
            'type': 'checkin'
            })
        self.finger_template = self.env['finger.template'].create({
            'uid': 1,
            'fid': 1,
            'device_user_id': self.attendance_device_user.id,
            'device_id': self.attendance_device.id,
            })
        self.hr_attendance = self.env['hr.attendance']
        self.user_attendance = self.env['user.attendance'].create({
            'device_id': self.attendance_device.id,
            'user_id': self.attendance_device_user.id,
            'timestamp': fields.Datetime.now(),
            'status': 100,
            'attendance_state_id': self.attendance_state.id
            })
