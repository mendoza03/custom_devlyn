# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MenuRestrictionGroup(models.Model):
    _name = "menu.restriction.group"
    _description = "Menu Restriction Group"
    _order = "name"

    name = fields.Char(string="Group Name", required=True)
    active = fields.Boolean(string="Active", default=True)

    user_ids = fields.Many2many(
        "res.users",
        "menu_restriction_group_users_rel",
        "group_id",
        "user_id",
        string="Users",
    )
    hide_menu_ids = fields.Many2many(
        "ir.ui.menu",
        "menu_restriction_group_menus_rel",
        "group_id",
        "menu_id",
        string="Hidden Menus",
    )
    permission_ids = fields.One2many(
        "menu.restriction.permission",
        "restriction_group_id",
        string="Menu Permissions",
    )
    hidden_button_ids = fields.One2many(
        "menu.restriction.button",
        "restriction_group_id",
        string="Hidden Buttons",
    )
    hidden_report_ids = fields.One2many(
        "menu.restriction.report",
        "restriction_group_id",
        string="Hidden Reports",
    )
    res_group_id = fields.Many2one(
        "res.groups",
        string="Security Group",
        readonly=True,
        copy=False,
        help="Auto-generated security group used for record rules",
    )

    user_count = fields.Integer(compute="_compute_user_count", store=True)
    menu_count = fields.Integer(compute="_compute_menu_count", store=True)
    permission_count = fields.Integer(compute="_compute_permission_count", store=True)
    button_count = fields.Integer(compute="_compute_button_count", store=True)
    report_count = fields.Integer(compute="_compute_report_count", store=True)

    @api.depends("user_ids")
    def _compute_user_count(self):
        for record in self:
            record.user_count = len(record.user_ids)

    @api.depends("hide_menu_ids")
    def _compute_menu_count(self):
        for record in self:
            record.menu_count = len(record.hide_menu_ids)

    @api.depends("permission_ids")
    def _compute_permission_count(self):
        for record in self:
            record.permission_count = len(record.permission_ids)

    @api.depends("hidden_button_ids")
    def _compute_button_count(self):
        for record in self:
            record.button_count = len(record.hidden_button_ids)

    @api.depends("hidden_report_ids")
    def _compute_report_count(self):
        for record in self:
            record.report_count = len(record.hidden_report_ids)

    def _get_or_create_res_group(self):
        self.ensure_one()
        if not self.res_group_id:
            res_group = self.env["res.groups"].sudo().create({
                "name": "Menu Restriction: %s" % self.name,
                "category_id": self.env.ref("base.module_category_hidden").id,
            })
            self.sudo().write({"res_group_id": res_group.id})
        return self.res_group_id

    def _sync_res_group_users(self):
        for record in self:
            if record.res_group_id:
                record.res_group_id.sudo().write({
                    "users": [(6, 0, record.user_ids.ids)]
                })

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._get_or_create_res_group()
            record._sync_res_group_users()
            if record.active:
                for menu in record.hide_menu_ids:
                    for user in record.user_ids:
                        menu.sudo().write({"restrict_user_ids": [(4, user.id)]})
        return records

    def write(self, vals):
        old_values = {
            r.id: {
                "user_ids": r.user_ids,
                "hide_menu_ids": r.hide_menu_ids,
                "active": r.active,
            }
            for r in self
        }
        res = super().write(vals)
        for record in self:
            old = old_values[record.id]
            record._get_or_create_res_group()
            record._sync_res_group_users()
            if old["active"] and not record.active:
                for menu in record.hide_menu_ids:
                    for user in record.user_ids:
                        menu.sudo().write({"restrict_user_ids": [(3, user.id)]})
                continue
            if not old["active"] and record.active:
                for menu in record.hide_menu_ids:
                    for user in record.user_ids:
                        menu.sudo().write({"restrict_user_ids": [(4, user.id)]})
                continue
            if record.active:
                for menu in record.hide_menu_ids - old["hide_menu_ids"]:
                    for user in record.user_ids:
                        menu.sudo().write({"restrict_user_ids": [(4, user.id)]})
                for menu in old["hide_menu_ids"] - record.hide_menu_ids:
                    for user in record.user_ids:
                        if menu not in user.hide_menu_ids and not self.search([
                            ("id", "!=", record.id), ("active", "=", True),
                            ("user_ids", "in", user.id), ("hide_menu_ids", "in", menu.id),
                        ]):
                            menu.sudo().write({"restrict_user_ids": [(3, user.id)]})
                for user in record.user_ids - old["user_ids"]:
                    for menu in record.hide_menu_ids:
                        menu.sudo().write({"restrict_user_ids": [(4, user.id)]})
                for user in old["user_ids"] - record.user_ids:
                    for menu in record.hide_menu_ids:
                        if menu not in user.hide_menu_ids and not self.search([
                            ("id", "!=", record.id), ("active", "=", True),
                            ("user_ids", "in", user.id), ("hide_menu_ids", "in", menu.id),
                        ]):
                            menu.sudo().write({"restrict_user_ids": [(3, user.id)]})
        return res

    def unlink(self):
        for record in self:
            for menu in record.hide_menu_ids:
                for user in record.user_ids:
                    if menu not in user.hide_menu_ids and not self.search([
                        ("id", "!=", record.id), ("active", "=", True),
                        ("user_ids", "in", user.id), ("hide_menu_ids", "in", menu.id),
                    ]):
                        menu.sudo().write({"restrict_user_ids": [(3, user.id)]})
            if record.res_group_id:
                record.res_group_id.sudo().unlink()
        return super().unlink()

    def action_view_users(self):
        self.ensure_one()
        return {
            "name": "Users in " + self.name,
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "view_mode": "list,form",
            "domain": [("id", "in", self.user_ids.ids)],
            "context": {"create": False},
        }

    def action_view_menus(self):
        self.ensure_one()
        return {
            "name": "Hidden Menus in " + self.name,
            "type": "ir.actions.act_window",
            "res_model": "ir.ui.menu",
            "view_mode": "list,form",
            "domain": [("id", "in", self.hide_menu_ids.ids)],
            "context": {"create": False},
        }

    def action_view_permissions(self):
        self.ensure_one()
        return {
            "name": "Permission Rules for " + self.name,
            "type": "ir.actions.act_window",
            "res_model": "menu.restriction.permission",
            "view_mode": "list,form",
            "domain": [("id", "in", self.permission_ids.ids)],
            "context": {"default_restriction_group_id": self.id, "create": True},
        }

    def action_view_buttons(self):
        self.ensure_one()
        return {
            "name": "Hidden Buttons in " + self.name,
            "type": "ir.actions.act_window",
            "res_model": "menu.restriction.button",
            "view_mode": "list,form",
            "domain": [("id", "in", self.hidden_button_ids.ids)],
            "context": {"default_restriction_group_id": self.id, "create": True},
        }

    def action_view_reports(self):
        self.ensure_one()
        return {
            "name": "Hidden Reports in " + self.name,
            "type": "ir.actions.act_window",
            "res_model": "menu.restriction.report",
            "view_mode": "list,form",
            "domain": [("id", "in", self.hidden_report_ids.ids)],
            "context": {"default_restriction_group_id": self.id, "create": True},
        }