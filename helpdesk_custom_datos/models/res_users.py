from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = "res.users"

    x_branch_id = fields.Many2one(
        "devlyn.catalog.branch",
        string="Sucursal",
        domain=[("active", "=", True)],
        ondelete="restrict",
    )

    sap_center_id = fields.Many2one(
        'helpdesk.sap.center',
        string='Centro SAP',
    )

    x_helpdesk_section_ids = fields.Many2many(
        "helpdesk.section",
        "res_users_helpdesk_section_rel",
        "user_id",
        "section_id",
        string="Secciones Helpdesk permitidas",
    )

    x_helpdesk_category_ids = fields.Many2many(
        "helpdesk.ticket.category",
        "res_users_helpdesk_category_rel",
        "user_id",
        "category_id",
        string="Categorias Helpdesk permitidas",
    )

    x_helpdesk_subcategory_ids = fields.Many2many(
        "helpdesk.ticket.subcategory",
        "res_users_helpdesk_subcategory_rel",
        "user_id",
        "subcategory_id",
        string="Subcategorias Helpdesk permitidas",
    )

    @api.onchange('sap_center_id')
    def _onchange_sap_center_id(self):
        for rec in self:
            rec.x_branch_id = rec.sap_center_id.x_branch_id

    @api.onchange("x_helpdesk_section_ids")
    def _onchange_x_helpdesk_section_ids(self):
        for rec in self:
            if not rec.x_helpdesk_section_ids:
                continue
            rec.x_helpdesk_category_ids = rec.x_helpdesk_category_ids.filtered(
                lambda category: category.section_id in rec.x_helpdesk_section_ids
            )
            rec.x_helpdesk_subcategory_ids = rec.x_helpdesk_subcategory_ids.filtered(
                lambda subcategory: subcategory.category_id.section_id in rec.x_helpdesk_section_ids
            )

    @api.onchange("x_helpdesk_category_ids")
    def _onchange_x_helpdesk_category_ids(self):
        for rec in self:
            if rec.x_helpdesk_category_ids:
                rec.x_helpdesk_section_ids |= rec.x_helpdesk_category_ids.mapped("section_id")
                rec.x_helpdesk_subcategory_ids = rec.x_helpdesk_subcategory_ids.filtered(
                    lambda subcategory: subcategory.category_id in rec.x_helpdesk_category_ids
                )

    @api.onchange("x_helpdesk_subcategory_ids")
    def _onchange_x_helpdesk_subcategory_ids(self):
        for rec in self:
            if rec.x_helpdesk_subcategory_ids:
                categories = rec.x_helpdesk_subcategory_ids.mapped("category_id")
                rec.x_helpdesk_category_ids |= categories
                rec.x_helpdesk_section_ids |= categories.mapped("section_id")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            sap_center_id = vals.get('sap_center_id')

            if sap_center_id and not vals.get('x_branch_id'):
                sap_center = self.env['helpdesk.sap.center'].browse(sap_center_id)
                vals['x_branch_id'] = sap_center.x_branch_id.id

        return super().create(vals_list)

    def write(self, vals):
        if vals.get('sap_center_id'):
            sap_center = self.env['helpdesk.sap.center'].browse(vals['sap_center_id'])
            vals['x_branch_id'] = sap_center.x_branch_id.id

        return super().write(vals)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "x_branch_id",
            "sap_center_id",
            "x_helpdesk_section_ids",
            "x_helpdesk_category_ids",
            "x_helpdesk_subcategory_ids",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            "x_branch_id",
            "sap_center_id",
            "x_helpdesk_section_ids",
            "x_helpdesk_category_ids",
            "x_helpdesk_subcategory_ids",
        ]
