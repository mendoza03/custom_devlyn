from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    asesor = fields.Many2one(
        "hr.employee",
        string="Asesor",
        ondelete="set null",
        domain=[("active", "=", True)],
    )
    gerente = fields.Many2one(
        "hr.employee",
        string="Gerente",
        ondelete="set null",
        domain=[("active", "=", True)],
    )
    dvn = fields.Many2one(
        "hr.employee",
        string="DVN",
        ondelete="set null",
        domain=[("active", "=", True)],
    )
    cco = fields.Many2one(
        "hr.employee",
        string="CCO",
        ondelete="set null",
        domain=[("active", "=", True)],
    )
    kam = fields.Many2one(
        "hr.employee",
        string="KAM",
        ondelete="set null",
        domain=[("active", "=", True)],
    )
