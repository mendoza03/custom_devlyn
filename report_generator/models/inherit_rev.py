# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _


class InheritREV(models.Model):
    _inherit = 'rev.crm.contract.brief'

    def action_open_contract(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Open Contract"),
            "res_model": "mm.open.contract.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": self._name,
                "active_id": self.id,
            },
        }


class MmOpenContractWizard(models.TransientModel):
    _name = "mm.open.contract.wizard"
    _description = "Open Contract Wizard"

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)

    template_id = fields.Many2one(
        comodel_name="mm.contract.template",
        string="Contract Template",
        required=True,
        domain=[('active', '=', True)],
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # Prefer the active record that launched the wizard
        ctx = self.env.context
        active_model = ctx.get("active_model")
        active_id = ctx.get("active_id")

        if active_model and active_id:
            res["res_model"] = active_model
            res["res_id"] = active_id

        # Preselect first active template if any
        if "template_id" in fields_list and not res.get("template_id"):
            template = self.env["mm.contract.template"].search([("active", "=", True)], limit=1)
            if template:
                res["template_id"] = template.id

        return res

    def action_confirm(self):
        self.ensure_one()

        if not self.template_id:
            raise UserError(_("Please select a contract template."))

        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError(_("The source record no longer exists."))

        doc = self.env["mm.contract.document"].create({
            "name": f"Contract - {getattr(record, 'full_name', record.display_name)}",
            "template_id": self.template_id.id,
            "res_model": self.res_model,
            "res_id": self.res_id,
        })
        doc.action_render()

        return {
            "type": "ir.actions.act_window",
            "res_model": "mm.contract.document",
            "view_mode": "form",
            "res_id": doc.id,
            "target": "current",
        }