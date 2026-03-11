from odoo import api, fields, models


class HelpdeskSection(models.Model):
    _name = "helpdesk.section"
    _description = "Helpdesk Section"
    _order = "sequence, name, id"

    name = fields.Char(required=True, translate=False)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("helpdesk_section_name_uniq", "unique(name)", "This section already exists."),
    ]