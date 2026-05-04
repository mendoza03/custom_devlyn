# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PropertySalesClusterSummaryGenerator(models.TransientModel):
    _name = "property.sales.cluster.summary.generator"
    _description = "Generate Cluster Sales Summary"

    cluster_id = fields.Many2one(
        "project.worksite",
        string="Cluster",
        required=True,
    )

    calendar_id = fields.Many2one(
        "sale.goal.calendar",
        string="Calendar",
        required=True,
    )

    def action_generate(self):
        """Generate cluster summary"""
        self.ensure_one()

        # Verificar que sea un cluster (no tenga parent_id)
        if self.cluster_id.parent_id:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "Debes seleccionar un Cluster (no una obra individual).",
                    "type": "warning",
                },
            }

        # Limpiar registro existente usando SQL directo
        self.env.cr.execute("""
            DELETE FROM property_sales_cluster_summary
            WHERE cluster_id = %s AND calendar_id = %s
        """, (self.cluster_id.id, self.calendar_id.id))

        # Crear nuevo registro
        self.env["property.sales.cluster.summary"].create({
            "cluster_id": self.cluster_id.id,
            "calendar_id": self.calendar_id.id,
        })

        # Abrir el registro creado
        return {
            "type": "ir.actions.act_window",
            "name": "Resumen del Cluster",
            "res_model": "property.sales.cluster.summary",
            "view_mode": "form,list",
            "domain": [
                ("cluster_id", "=", self.cluster_id.id),
                ("calendar_id", "=", self.calendar_id.id),
            ],
            "target": "current",
        }