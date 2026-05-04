# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PropertySalesSummaryGenerator(models.TransientModel):
    _name = "property.sales.summary.generator"
    _description = "Generate Sales Summary for All Worksites"

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
        """Generate summary records for all worksites in the cluster"""
        self.ensure_one()

        # Obtener todos los worksites del cluster
        worksites = self.env["project.worksite"].search([
            ("parent_id", "=", self.cluster_id.id)
        ])

        if not worksites:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "No se encontraron obras en este cluster.",
                    "type": "warning",
                },
            }

        # Limpiar registros existentes usando SQL directo
        self.env.cr.execute("""
            DELETE FROM property_sales_summary
            WHERE cluster_id = %s AND calendar_id = %s
        """, (self.cluster_id.id, self.calendar_id.id))

        # Crear un registro por cada worksite
        for worksite in worksites:
            self.env["property.sales.summary"].create({
                "cluster_id": self.cluster_id.id,
                "worksite_id": worksite.id,
                "calendar_id": self.calendar_id.id,
            })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Generado",
                "message": f"Se generaron {len(worksites)} registros correctamente.",
                "type": "success",
            },
        }