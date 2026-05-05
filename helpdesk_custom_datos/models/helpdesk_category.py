from odoo import fields, models


class HelpdeskTicketCategory(models.Model):
    _name = "helpdesk.ticket.category"
    _description = "Helpdesk Ticket Category"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    section_id = fields.Many2one("helpdesk.section", string="Sección", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("helpdesk_ticket_category_uniq", "unique(name, section_id)", "Category already exists for this section."),
    ]


class HelpdeskTicketSubcategory(models.Model):
    _name = "helpdesk.ticket.subcategory"
    _description = "Helpdesk Ticket Subcategory"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    category_id = fields.Many2one("helpdesk.ticket.category", required=True, ondelete="cascade")
    user_ids = fields.Many2many(
        "res.users",
        "helpdesk_ticket_subcategory_res_users_rel",
        "subcategory_id",
        "user_id",
        string="Usuarios asignables",
        domain=[("share", "=", False)],
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    code = fields.Char(string="Código", index=True)
