import logging
from random import randint

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from ..pyzk.zk.exception import ZKErrorResponse

_logger = logging.getLogger(__name__)


class AttendanceDeviceUser(models.Model):
    _name = 'attendance.device.user'
    _inherit = 'mail.thread'
    _description = 'Attendance Machine User'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(string='Name', help="The name of the employee stored in the machine", required=True, tracking=True)
    device_id = fields.Many2one('attendance.device', string='Attendance Machine', required=True, ondelete='cascade', tracking=True, index=True)
    uid = fields.Integer(string='UID', help="The ID (technical field) of the user/employee in the machine storage", readonly=True, tracking=True)
    user_id = fields.Char(string='ID Number', size=8, help="The ID Number of the user/employee in the machine storage", required=True, tracking=True)
    password = fields.Char(string='Password', tracking=True, help="Used when checkin/checkout on the attendance machines by password")
    group_id = fields.Integer(string='Group', default=0, tracking=True, help="Group ID of the user on the attendance machines")
    privilege = fields.Integer(string='Privilege', tracking=True, help="Privilege of the user on the attendance machines")
    del_user = fields.Boolean(string='Delete In Machine?', default=False,
                              tracking=True,
                              help="If checked, the user on the machine will be deleted upon deleting this record in System")
    employee_id = fields.Many2one('hr.employee', string='Employee', help="The Employee who is corresponding to this machine user",
                                  ondelete='set null', tracking=True, index=True)
    attendance_ids = fields.One2many('user.attendance', 'user_id', string='Attendance Data', readonly=True)
    attendance_id = fields.Many2one('user.attendance', string='Current Attendance', store=True,
                                    compute='_compute_current_attendance',
                                    help="The technical field to store current attendance recorded of the user.")
    active = fields.Boolean(string='Active',
                            compute='_compute_get_active', store=True, precompute=True,
                            default=True, tracking=True, readonly=False)
    finger_templates_ids = fields.One2many('finger.template', 'device_user_id', string='Finger Template', readonly=True)
    total_finger_template_records = fields.Integer(string='Finger Templates', compute='_compute_total_finger_template_records')
    bio_templates_ids = fields.One2many('bio.template', 'device_user_id', string='Bio Template', readonly=True)
    total_bio_template_records = fields.Integer(string='Biometric Templates', compute='_compute_total_bio_template_records')
    not_in_device = fields.Boolean(string='Not in machine', readonly=True, help="Technical field to indicate this user is not available in machine storage."
                                 " It could be deleted outside System.")
    color = fields.Integer('Color Index', default=_get_default_color)

    _employee_device_unique = models.Constraint(
        'unique(employee_id, device_id)',
        "The Employee must be unique per machine",
    )

    def _compute_total_finger_template_records(self):
        data = self.env['finger.template']._read_group(
            [('device_user_id', 'in', self.ids)], ['device_user_id'], ['__count'])
        mapped_data = {device_user.id: count for device_user, count in data}
        for r in self:
            r.total_finger_template_records = mapped_data.get(r.id, 0)

    def _compute_total_bio_template_records(self):
        data = self.env['bio.template']._read_group(
            [('device_user_id', 'in', self.ids)], ['device_user_id'], ['__count'])
        mapped_data = {device_user.id: count for device_user, count in data}
        for r in self:
            r.total_bio_template_records = mapped_data.get(r.id, 0)

    @api.depends('device_id', 'device_id.active', 'employee_id', 'employee_id.active')
    def _compute_get_active(self):
        for r in self:
            if r.employee_id:
                r.active = r.device_id.active and r.employee_id.active
            else:
                r.active = r.device_id.active

    @api.depends('attendance_ids')
    def _compute_current_attendance(self):
        for r in self:
            r.attendance_id = self.env['user.attendance'].search([('user_id', '=', r.id)], limit=1, order='timestamp DESC') or False

    @api.constrains('user_id', 'device_id')
    def constrains_user_id_device_id(self):
        for r in self:
            if r.device_id and r.device_id.unique_uid:
                duplicate = self.search([('id', '!=', r.id), ('device_id', '=', r.device_id.id), ('user_id', '=', r.user_id)], limit=1)
                if duplicate:
                    raise UserError(_("The ID Number must be unique per machine!"
                                      " A new user was being created/updated whose user_id and"
                                      " machine_id is the same as the existing one's (name: %(name)s; machine: %(machine)s; user_id: %(user_id)s)",
                                      name=duplicate.name, machine=duplicate.device_id.display_name, user_id=duplicate.user_id)
                                      )

    def unlink(self):
        to_del_dev_users = self.filtered('del_user')
        remaining = self - to_del_dev_users
        for r in to_del_dev_users:
            try:
                # to avoid inconsistent data, delete attendance device users only if it
                # was successfully deleted from device
                with r.env.cr.savepoint():
                    r.device_id.delUser(r.uid, r.user_id)
                    remaining |= r
            except ZKErrorResponse as e:
                # when try to delete a user that does not exist in device, exception ZKErrorResponse will raise
                # catch this exception to allow to delete this user in Odoo
                if "Can't delete user" in '%s' % e:
                    remaining |= r
                else:
                    _logger.error(e)
            except Exception as e:
                _logger.error(e)
        remaining.finger_templates_ids.unlink()
        remaining.bio_templates_ids.unlink()
        super(AttendanceDeviceUser, remaining).unlink()
        return True

    def setUser(self):
        self.ensure_one()
        new_user = self.device_id.setUser(
            self.uid,
            self.name,
            self.privilege,
            self.password,
            str(self.group_id),
            str(self.user_id))
        if self.device_id.support_biometric:
            self.upload_bio_templates()
        else:
            self.upload_finger_templates()
        return new_user

    def upload_finger_templates(self):
        finger_templates = self.finger_templates_ids
        if self.employee_id:
            new_finger_templates = self.env['finger.template'].search(
                [('employee_id', '=', self.employee_id.id),
                ('template', 'not in', finger_templates.mapped('template'))])
            if new_finger_templates:
                vals_list = []
                for finger_template in new_finger_templates:
                    vals_list.append({
                        'device_user_id': self.id,
                        'fid': finger_template.fid,
                        'valid': finger_template.valid,
                        'template': finger_template.template,
                        'employee_id': self.employee_id.id
                    })
                finger_templates += self.env['finger.template'].create(vals_list)
        finger_templates.upload_to_device()

    def upload_bio_templates(self):
        self.ensure_one()
        bio_templates = self.bio_templates_ids
        if self.employee_id:
            new_bio_templates = self.env['bio.template'].search(
                [('employee_id', '=', self.employee_id.id),
                ('template', 'not in', bio_templates.mapped('template'))])
            if new_bio_templates:
                vals_list = []
                for bio_template in new_bio_templates:
                    vals_list.append({
                        'device_user_id': self.id,
                        'employee_id': self.employee_id.id,
                        'user_id': self.user_id,
                        'number': bio_template.number,
                        'index': bio_template.index,
                        'valid': bio_template.valid,
                        'duress': bio_template.duress,
                        'type_bio': bio_template.type_bio,
                        'major_ver': bio_template.major_ver,
                        'minor_ver': bio_template.minor_ver,
                        'format_bio': bio_template.format_bio,
                        'template': bio_template.template,
                    })
                bio_templates += self.env['bio.template'].create(vals_list)
        bio_templates.upload_to_device()

    def action_upload_finger_templates(self):
        for r in self:
            if r.total_finger_template_records > 0 and not r.device_id.support_biometric:
                r.upload_finger_templates()
            if r.total_bio_template_records > 0 and r.device_id.support_biometric:
                r.upload_bio_templates()

    @api.model_create_multi
    def create(self, vals_list):
        users = super(AttendanceDeviceUser, self).create(vals_list)
        # TODO: Không tìm thấy context should_set_user được truyền ở đâu.
        # Xem sét bỏ context này trên ver cao hơn
        if self.env.context.get('should_set_user', False):
            for user in users:
                user.setUser()
        return users

    def _prepare_employee_data(self, barcode=None):
        barcode = barcode or self.user_id
        return {
            'name': self.name,
            'created_from_attendance_device': True,
            'barcode': barcode,
            'device_user_ids': [(4, self.id)]
            }

    def generate_employees(self):
        """
        This method will generate new employees from the machine user data.
        """
        # prepare employees data
        employee_vals_list = []
        for r in self:
            employee_vals_list.append(r._prepare_employee_data())

        # generate employees
        if employee_vals_list:
            return self.env['hr.employee'].sudo().create(employee_vals_list)

        return self.env['hr.employee']

    def smart_find_employee(self):
        self.ensure_one()
        employee_id = False
        if self.employee_id:
            employee_id = self.employee_id
        else:
            for employee in self.device_id.unmapped_employee_ids:
                if self.user_id == employee.barcode \
                or self.name == employee.name \
                or self.name.lower() == employee._get_unaccent_name().lower() \
                or self.name == employee.name[:len(self.name)]:
                    employee_id = employee
        return employee_id

    def action_view_finger_template(self):
        result = self.env['ir.actions.act_window']._for_xml_id('to_attendance_device.action_finger_template')

        # reset context
        result['context'] = {}
        # choose the view_mode accordingly
        total_finger_template_records = self.total_finger_template_records
        if total_finger_template_records != 1:
            result['domain'] = "[('device_user_id', 'in', " + str(self.ids) + ")]"
        elif total_finger_template_records == 1:
            res = self.env.ref('to_attendance_device.view_finger_template_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.finger_templates_ids.id
        return result

    def action_view_bio_template(self):
        result = self.env['ir.actions.act_window']._for_xml_id('to_attendance_device.action_bio_template')
        result['context'] = {}
        total_bio_template_records = self.total_bio_template_records
        if total_bio_template_records != 1:
            result['domain'] = "[('device_user_id', 'in', " + str(self.ids) + ")]"
        elif total_bio_template_records == 1:
            res = self.env.ref('to_attendance_device.view_bio_template_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.bio_templates_ids.id
        return result

    def write(self, vals):
        res = super(AttendanceDeviceUser, self).write(vals)
        for r in self:
            if r.env.context.get('write_new_data_user_to_device', False):
                r.setUser()
        return res

    @api.depends('name')
    def _compute_display_name(self):
        protocol = dict(self.env['attendance.device']._fields['protocol']._description_selection(self.env))
        for r in self:
            r.display_name = "{}-{}-{}".format(str(r.name), str(r.device_id.name), str(protocol.get(r.device_id.protocol, False)))
