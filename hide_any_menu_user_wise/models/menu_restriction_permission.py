# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

DOMAIN_PRESETS = [
    ("own_user_id",    "Solo mis registros (user_id)"),
    ("own_create_uid", "Solo mis registros (create_uid)"),
    ("own_team",       "Solo mi equipo (team_id)"),
    ("own_company",    "Solo mi empresa (company_id)"),
    ("custom",         "Dominio personalizado"),
]

PRESET_DOMAIN_MAP = {
    "own_user_id":    "[('user_id', '=', user.id)]",
    "own_create_uid": "[('create_uid', '=', user.id)]",
    "own_team":       "[('team_id.member_ids', 'in', [user.id])]",
    "own_company":    "[('company_id', '=', user.company_id.id)]",
}


class MenuRestrictionPermission(models.Model):
    _name = "menu.restriction.permission"
    _description = "Menu Restriction Permission"
    _order = "restriction_group_id, menu_id"

    restriction_group_id = fields.Many2one(
        "menu.restriction.group",
        string="Restriction Group",
        required=True,
        ondelete="cascade",
    )
    menu_id = fields.Many2one(
        "ir.ui.menu",
        string="Menu",
        required=True,
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        compute="_compute_model_id",
        store=True,
    )
    model_name = fields.Char(
        string="Model Name",
        related="model_id.model",
        store=True,
    )
    perm_read = fields.Boolean(string="Read", default=True)
    perm_write = fields.Boolean(string="Write", default=True)
    perm_create = fields.Boolean(string="Create", default=True)
    perm_unlink = fields.Boolean(string="Delete", default=True)
    active = fields.Boolean(string="Active", default=True)
    apply_to_all_users = fields.Boolean(string="Apply to All Group Users", default=True)
    specific_user_ids = fields.Many2many(
        "res.users",
        "menu_restriction_permission_users_rel",
        "permission_id",
        "user_id",
        string="Specific Users",
    )

    # Domain filter fields
    apply_domain = fields.Boolean(
        string="Apply Domain Filter",
        default=False,
        help="If enabled, users in this group will only see records matching the domain below",
    )
    domain_preset = fields.Selection(
        selection=DOMAIN_PRESETS,
        string="Domain Preset",
        help="Select a common filter or choose 'Custom' to write your own domain",
    )
    domain = fields.Char(
        string="Domain",
        default="[]",
        help="Domain filter to restrict visible records. Available variable: user (current user record)",
    )
    ir_rule_id = fields.Many2one(
        "ir.rule",
        string="Record Rule",
        readonly=True,
        copy=False,
        help="Auto-generated record rule for this domain filter",
    )

    _sql_constraints = [
        (
            "unique_group_menu",
            "UNIQUE(restriction_group_id, menu_id)",
            "This menu already has permissions configured for this group!",
        )
    ]

    @api.depends("menu_id")
    def _compute_model_id(self):
        for record in self:
            model_id = False
            if record.menu_id and record.menu_id.action:
                action = record.menu_id.action
                if hasattr(action, "_name"):
                    if action._name == "ir.actions.act_window" and action.res_model:
                        model_id = self.env["ir.model"].search(
                            [("model", "=", action.res_model)], limit=1
                        )
            record.model_id = model_id

    @api.onchange("domain_preset")
    def _onchange_domain_preset(self):
        for record in self:
            if record.domain_preset and record.domain_preset != "custom":
                record.domain = PRESET_DOMAIN_MAP.get(record.domain_preset, "[]")
            elif record.domain_preset == "custom":
                record.domain = "[]"

    def _sync_ir_rule(self):
        """Create, update or delete the ir.rule based on apply_domain state."""
        for record in self:
            if record.apply_domain and record.domain and record.domain != "[]" and record.model_id and record.active:
                res_group = record.restriction_group_id._get_or_create_res_group()
                rule_vals = {
                    "name": "Menu Restriction: %s - %s" % (
                        record.restriction_group_id.name,
                        record.model_name,
                    ),
                    "model_id": record.model_id.id,
                    "domain_force": record.domain,
                    "groups": [(6, 0, [res_group.id])],
                    "perm_read": True,
                    "perm_write": True,
                    "perm_create": True,
                    "perm_unlink": True,
                    "active": True,
                }
                if record.ir_rule_id:
                    record.ir_rule_id.sudo().write(rule_vals)
                else:
                    ir_rule = self.env["ir.rule"].sudo().create(rule_vals)
                    record.sudo().write({"ir_rule_id": ir_rule.id})
            else:
                if record.ir_rule_id:
                    record.ir_rule_id.sudo().unlink()
                    record.sudo().write({"ir_rule_id": False})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_ir_rule()
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ("apply_domain", "domain", "domain_preset", "active", "model_id")):
            self._sync_ir_rule()
        return res

    def unlink(self):
        for record in self:
            if record.ir_rule_id:
                record.ir_rule_id.sudo().unlink()
        return super().unlink()

    @api.constrains("apply_to_all_users", "specific_user_ids")
    def _check_specific_users(self):
        for record in self:
            if not record.apply_to_all_users and not record.specific_user_ids:
                raise ValidationError(
                    _("Please select at least one specific user or enable 'Apply to All Group Users'.")
                )

    @api.constrains("specific_user_ids", "restriction_group_id")
    def _check_users_in_group(self):
        for record in self:
            if record.specific_user_ids:
                users_not_in_group = record.specific_user_ids - record.restriction_group_id.user_ids
                if users_not_in_group:
                    raise ValidationError(
                        _("The following users are not members of the restriction group '%s': %s") % (
                            record.restriction_group_id.name,
                            ", ".join(users_not_in_group.mapped("name")),
                        )
                    )

    def name_get(self):
        result = []
        for record in self:
            name = "%s - %s" % (
                record.restriction_group_id.name,
                record.menu_id.complete_name,
            )
            result.append((record.id, name))
        return result