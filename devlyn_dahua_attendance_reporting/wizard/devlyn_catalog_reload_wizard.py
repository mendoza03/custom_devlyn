import json

from odoo import fields, models


class DevlynCatalogReloadWizard(models.TransientModel):
    _name = "devlyn.catalog.reload.wizard"
    _description = "Asistente para Recargar Catalogos Devlyn"

    load_summary = fields.Text(
        readonly=True,
        string="Resultado",
        default="Utiliza esta accion para recargar los catalogos empaquetados del addon.",
    )

    def action_reload_catalogs(self):
        self.ensure_one()
        results = self.env["devlyn.catalog.loader.service"].load_all()
        self.load_summary = json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True)
        return {
            "type": "ir.actions.act_window",
            "name": "Recargar catálogos Devlyn",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
