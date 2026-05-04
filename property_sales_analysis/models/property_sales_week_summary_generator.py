# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PropertySalesWeekSummaryGenerator(models.TransientModel):
    _name = "property.sales.week.summary.generator"
    _description = "Generate Weekly Sales Summary"

    calendar_id = fields.Many2one(
        "sale.goal.calendar",
        string="Calendar",
        required=True,
    )

    def action_generate(self):
        """Generate weekly summaries for entire calendar"""
        self.ensure_one()

        # Limpiar usando SQL directo para evitar problemas de foreign keys
        self.env.cr.execute("""
            DELETE FROM property_sales_week_property_detail
            WHERE calendar_id = %s
        """, (self.calendar_id.id,))

        self.env.cr.execute("""
            DELETE FROM property_sales_week_cluster_summary
            WHERE calendar_id = %s
        """, (self.calendar_id.id,))

        self.env.cr.execute("""
            DELETE FROM property_sales_week_cluster_detail
            WHERE calendar_id = %s
        """, (self.calendar_id.id,))

        self.env.cr.execute("""
            DELETE FROM property_sales_week_summary
            WHERE calendar_id = %s
        """, (self.calendar_id.id,))

        # Obtener TODOS los meses del calendario
        calendar_months = self.env["sale.goal.calendar.month"].search([
            ("calendar_id", "=", self.calendar_id.id)
        ], order="month_number")

        if not calendar_months:
            raise UserError(_(
                "El calendario '%s' no tiene meses configurados."
            ) % self.calendar_id.name)

        # Obtener TODAS las semanas
        all_weeks = []
        for month in calendar_months:
            month_weeks = self.env["sale.goal.calendar.week"].search([
                ("month_id", "=", month.id)
            ], order="week_number")
            all_weeks.extend(month_weeks)

        if not all_weeks:
            raise UserError(_(
                "El calendario '%s' no tiene semanas configuradas."
            ) % self.calendar_id.name)

        # Obtener TODOS los clusters del sistema (worksites sin padre)
        all_clusters = self.env["project.worksite"].search([
            ("parent_id", "=", False)
        ], order="name")

        if not all_clusters:
            raise UserError(_(
                "No se encontraron clusters en el sistema.\n\n"
                "Verifica que existan worksites sin parent_id."
            ))

        # Obtener TODAS las obras de TODOS los clusters
        cluster_worksites = {}
        total_worksites = 0
        
        for cluster in all_clusters:
            worksites = self.env["project.worksite"].search([
                ("parent_id", "=", cluster.id)
            ], order="name")
            
            if worksites:
                cluster_worksites[cluster.id] = {
                    "cluster": cluster,
                    "worksites": worksites
                }
                total_worksites += len(worksites)

        if total_worksites == 0:
            raise UserError(_(
                "No se encontraron obras en ningún cluster.\n\n"
                "Los clusters encontrados no tienen worksites hijos."
            ))

        # Crear un registro por cada semana
        week_count = 0
        detail_count = 0
        summary_count = 0
        
        for sequential_num, week in enumerate(all_weeks, 1):
            if sequential_num > 53:
                break
            
            # Crear el registro de semana
            week_summary = self.env["property.sales.week.summary"].create({
                "calendar_id": self.calendar_id.id,
                "week_number": sequential_num,
                "week_start": week.start_date,
                "week_end": week.end_date,
            })
            week_count += 1
            
            # Crear líneas CONSOLIDADAS por cluster
            for cluster_id, data in cluster_worksites.items():
                cluster = data["cluster"]
                
                self.env["property.sales.week.cluster.summary"].create({
                    "week_id": week_summary.id,
                    "cluster_id": cluster.id,
                    "sold_count": 0,
                    "sold_amount": 0.0,
                })
                summary_count += 1
            
            # Crear líneas DETALLADAS por cluster×obra
            for cluster_id, data in cluster_worksites.items():
                cluster = data["cluster"]
                worksites = data["worksites"]
                
                for worksite in worksites:
                    self.env["property.sales.week.cluster.detail"].create({
                        "week_id": week_summary.id,
                        "cluster_id": cluster.id,
                        "worksite_id": worksite.id,
                        "sold_count": 0,
                        "sold_amount": 0.0,
                    })
                    detail_count += 1

        # Mensaje informativo
        message = _(
            "Resumen generado exitosamente:\n\n"
            "• %s semanas creadas\n"
            "• %s clusters procesados\n"
            "• %s obras en total\n"
            "• %s líneas consolidadas creadas\n"
            "• %s líneas detalladas creadas\n\n"
            "Ahora ejecute 'Actualizar Datos' en cada semana para calcular las ventas.\n"
            "Las líneas de propiedades se crearán automáticamente al actualizar."
        ) % (week_count, len(cluster_worksites), total_worksites, summary_count, detail_count)

        # Abrir vista de lista
        return {
            "type": "ir.actions.act_window",
            "name": f"Resumen Semanal - {self.calendar_id.name}",
            "res_model": "property.sales.week.summary",
            "view_mode": "list,form",
            "domain": [("calendar_id", "=", self.calendar_id.id)],
            "context": {
                "create": False,
                "default_message": message,
            },
            "target": "current",
        }