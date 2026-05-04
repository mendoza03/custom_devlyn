# -*- coding: utf-8 -*-
from odoo import models, fields, api


class CrmLeadExpediente(models.Model):
    _inherit = "crm.lead"

    expediente_lead_id = fields.Many2one(
        "crm.lead",
        string="Expediente Lead",
        copy=False,
        index=True,
        help="Expediente lead generated when the original lead reaches the Apartado stage",
    )

    contract_stage = fields.Char(
        string="Contract Stage",
        compute="_compute_contract_stage",
        store=True,
    )

    contract_stage_text = fields.Char(
        string="Contract Stage",
        store=True,
    )

    origin_lead_id = fields.Many2one(
        "crm.lead",
        string="Origin Lead",
        copy=False,
        index=True,
        help="Original lead from which this expediente was generated",
    )

    @api.depends("expediente_lead_id", "expediente_lead_id.stage_id")
    def _compute_contract_stage(self):
        for record in self:
            if record.expediente_lead_id and record.expediente_lead_id.stage_id:
                record.contract_stage = record.expediente_lead_id.stage_id.name
                record.contract_stage_text = record.expediente_lead_id.stage_id.name
            else:
                record.contract_stage = False
                record.contract_stage_text = False

    def _compute_contract_brief(self):
        super()._compute_contract_brief()
        for lead in self:
            if not lead.expediente_lead_id:
                brief = lead.contract_brief_id
                if brief:
                    expediente = self.env["crm.lead"].search([
                        ("brief_id", "=", brief.id),
                        ("id", "!=", lead.id),
                    ], limit=1)
                    if expediente:
                        lead.expediente_lead_id = expediente.id
                        expediente.origin_lead_id = lead.id

    def action_open_expediente_lead(self):
        self.ensure_one()
        if not self.expediente_lead_id:
            return
        return {
            "type": "ir.actions.act_window",
            "name": "Expediente Lead",
            "res_model": "crm.lead",
            "res_id": self.expediente_lead_id.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        for lead in leads:
            if lead.brief_id and not lead.origin_lead_id:
                origin = self.env["crm.lead"].search([
                    ("contract_brief_id", "=", lead.brief_id.id),
                    ("id", "!=", lead.id),
                ], limit=1)
                if origin:
                    lead.origin_lead_id = origin.id
                    if not origin.expediente_lead_id:
                        origin.expediente_lead_id = lead.id
        return leads