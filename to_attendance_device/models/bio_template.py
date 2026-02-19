from odoo import models, fields, api
from .attendance_device import BioUserId


class BioTemplate(models.Model):
    _name = 'bio.template'
    _description = 'Bio Template Data'

    device_user_id = fields.Many2one('attendance.device.user',
        string='Machine User',
        index=True,
        help="The device user who is owner of this biometric template")
    employee_id = fields.Many2one('hr.employee',
        string='Employee',
        help="The employee who is owner of this biometric template", ondelete='cascade',
        compute='_compute_employee_id', store=True, readonly=False, index=True)
    device_id = fields.Many2one('attendance.device',
        string='Attendance Machine',
        related='device_user_id.device_id', store=True, index=True)
    user_id = fields.Char(string='ID Number',
        related='device_user_id.user_id',
        store=True,
        help="The ID Number of the user/employee in the machine storage. It is the PIN code of the user on the machine")
    number = fields.Integer(
        string='Biometric ID',
        default=0,
        help="Specific biological individual number, default value is 0.\n"
            "Fingerprint: Number is: 0-9, corresponding fingers are: \n"
            "Left hand: Little finger/Ring finger/Middle finger/Index finger/Thumb, \n"
            "Right hand: Thumb/Index finger/Middle finger/Ring finger/Little finger;\n"
            "Finger vein: Same as fingerprint\n"
            "Face: All are 0\n"
            "Iris: 0 for left eye, 1 for right eye\n"
            "Palm: 0 for left hand, 1 for right hand")
    index = fields.Integer(string='Index', help="The specific template sequence number in biometrics, for example,"
                                                "a finger can store multiple templates. Starts from 0")
    valid = fields.Integer(string='Valid', default=1, help="Validity indicator, 0: Invalid, 1: Valid")
    duress = fields.Integer(string='Duress', default=0, help="Indicates whether duress is present, 0: No duress, 1: Duress")
    type_bio = fields.Selection(
        selection=[
            ('0', 'General purpose'),
            ('1', 'Fingerprint'),
            ('2', 'Near-infrared face'),
            ('3', 'Voiceprint'),
            ('4', 'Iris'),
            ('5', 'Retinal image'),
            ('6', 'Palmprint'),
            ('7', 'Finger vein'),
            ('8', 'Palm vein'),
            ('9', 'Visible light face'),
        ],
        string='Biometric Type',
        help="Biometric Type")
    major_ver = fields.Integer(string='Major Version',
        help="Major version number, e.g., fingerprint algorithm version 10.3, the major version is 10, the minor version is 3")
    minor_ver = fields.Integer(string='Minor Version',
        help="Minor version number, e.g., fingerprint algorithm version 10.3, the major version is 10, the minor version is 3")
    version = fields.Char(string='Version', compute='_compute_version', help="Biometric algorithm version")
    format_bio = fields.Char(string='Format',
        default='0',
        help="Format Standards:\n"
        "Value = 0 or ZK: Format follows the ZKTeco standard.\n"
        "Value = 1 or ISO: Format follows the ISO standard.\n"
        "Value = 2 or ANSI: Format follows the ANSI standard.")
    template = fields.Binary(string='Template', attachment=False, help="Raw template data of BIODATA")
    active = fields.Boolean(string='Active', compute='_compute_active', default=True, store=True, readonly=False)

    @api.depends('device_id.active', 'employee_id.active')
    def _compute_active(self):
        for r in self:
            if r.employee_id:
                r.active = r.device_id.active and r.employee_id.active
            else:
                r.active = r.device_id.active

    @api.depends('device_user_id', 'device_user_id.employee_id')
    def _compute_employee_id(self):
        for r in self:
            if r.device_user_id and r.device_user_id.employee_id:
                r.employee_id = r.device_user_id.employee_id.id
            else:
                r.employee_id = r.employee_id

    @api.depends('major_ver', 'minor_ver')
    def _compute_version(self):
        for r in self:
            r.version = f"{r.major_ver}.{r.minor_ver}"

    def upload_to_device(self, devices=None):
        devices = devices or self.device_id
        device_users = self.device_user_id
        for device in devices:
            for user in device_users.filtered(lambda u: u.device_id == device):
                bio_templates = []
                for template in self.filtered(lambda t: t.device_user_id == user and t.device_id == device):
                    bio_template = BioUserId(
                        template.user_id,
                        template.number,
                        template.index,
                        template.valid,
                        template.duress,
                        template.type_bio,
                        template.major_ver,
                        template.minor_ver,
                        template.format_bio,
                        template.template
                    )
                    bio_templates.append(bio_template)
                if bio_templates:
                    device.upload_bio_templates(bio_templates)
