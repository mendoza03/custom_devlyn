# -*- coding: utf-8 -*-
from odoo import fields, models


class MenuRestrictionButton(models.Model):
    _name = "menu.restriction.button"
    _description = "Menu Restriction Hidden Button"
    _order = "restriction_group_id, model_id"

    restriction_group_id = fields.Many2one(
        "menu.restriction.group",
        string="Restriction Group",
        required=True,
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Model",
        required=True,
        ondelete="cascade",
    )
    model_name = fields.Char(
        string="Model Name",
        related="model_id.model",
        store=True,
    )
    button_name = fields.Char(
        string="Button Name",
        required=True,
        help="Value of the 'name' attribute of the button in the view XML. Example: action_confirm",
    )
    button_description = fields.Char(
        string="Description",
        help="Optional label to identify this button restriction",
    )
    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        (
            "unique_group_model_button",
            "UNIQUE(restriction_group_id, model_id, button_name)",
            "This button is already configured for this group and model!",
        )
    ]