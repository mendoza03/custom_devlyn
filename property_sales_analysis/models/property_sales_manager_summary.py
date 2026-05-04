# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class PropertySalesManagerSummary(models.Model):
    _name = "property.sales.manager.summary"
    _description = "Property Sales Summary by Manager"
    _order = "total_sold desc"

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
    )

    calendar_id = fields.Many2one(
        "sale.goal.calendar",
        string="Calendar",
        required=True,
    )

    calendar_name = fields.Char(
        string="Calendario",
        related="calendar_id.name",
        store=True,
    )

    manager_id = fields.Many2one(
        "hr.employee",
        string="Gerente",
        required=True,
    )

    manager_name = fields.Char(
        string="Gerente",
        related="manager_id.name",
        store=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    # Totals
    total_sold = fields.Integer(
        string="Total Vendido",
        compute="_compute_totals",
        store=True,
    )

    total_amount = fields.Float(
        string="Importe Total",
        compute="_compute_totals",
        store=True,
    )

    total_amount_display = fields.Char(
        string="Importe",
        compute="_compute_totals",
        store=True,
    )

    # Weekly breakdown
    weekly_details = fields.Text(
        string="Actividad por Semana",
        compute="_compute_totals",
        store=True,
    )

    # Cluster breakdown
    cluster_details = fields.Text(
        string="Ventas por Cluster",
        compute="_compute_totals",
        store=True,
    )

    # Properties list
    properties_list = fields.Text(
        string="Propiedades Vendidas",
        compute="_compute_totals",
        store=True,
    )

    # NUEVO: Líneas de detalle por semana
    week_detail_ids = fields.One2many(
        "property.sales.manager.week.detail",
        "manager_summary_id",
        string="Detalle por Semana",
    )

    @api.depends("manager_id", "calendar_id")
    def _compute_name(self):
        for record in self:
            if record.manager_id and record.calendar_id:
                record.name = f"{record.manager_id.name} - {record.calendar_id.name}"
            elif record.manager_id:
                record.name = record.manager_id.name
            else:
                record.name = "N/A"

    @api.depends("manager_id", "calendar_id")
    def _compute_totals(self):
        for record in self:
            # Limpiar líneas existentes
            record.week_detail_ids.unlink()
            
            if not record.manager_id or not record.calendar_id:
                record.total_sold = 0
                record.total_amount = 0.0
                record.total_amount_display = "$0.00"
                record.weekly_details = ""
                record.cluster_details = ""
                record.properties_list = ""
                continue

            # Verificar que el gerente existe
            manager_exists = self.env["res.users"].search([
                ("id", "=", record.manager_id.id)
            ], limit=1)

            if not manager_exists:
                record.total_sold = 0
                record.total_amount = 0.0
                record.total_amount_display = "$0.00"
                record.weekly_details = "Gerente no encontrado en el sistema"
                record.cluster_details = ""
                record.properties_list = ""
                continue

            # Obtener TODAS las propiedades apartadas por este gerente
            try:
                sold_properties = self.env["product.template"].search([
                    ("is_property", "=", True),
                    ("state", "=", "reserved"),
                    ("gerente", "=", record.manager_id.id),
                    ("date_state_change", "!=", False),
                ])
            except (KeyError, AttributeError):
                record.total_sold = 0
                record.total_amount = 0.0
                record.total_amount_display = "$0.00"
                record.weekly_details = "Campo 'gerente' no disponible"
                record.cluster_details = ""
                record.properties_list = ""
                continue

            record.total_sold = len(sold_properties)
            record.total_amount = sum(prop.final_amount or 0.0 for prop in sold_properties)
            record.total_amount_display = f"${record.total_amount:,.2f}"

            # Obtener TODAS las semanas del calendario
            calendar_months = self.env["sale.goal.calendar.month"].search([
                ("calendar_id", "=", record.calendar_id.id)
            ], order="month_number")

            all_weeks = []
            for month in calendar_months:
                month_weeks = self.env["sale.goal.calendar.week"].search([
                    ("month_id", "=", month.id)
                ], order="week_number")
                all_weeks.extend(month_weeks)

            # Agrupar por SEMANA
            weekly_data = {}
            cluster_data = {}

            for prop in sold_properties:
                # Encontrar en qué semana se vendió
                prop_date = prop.date_state_change.date()
                week_found = None
                sequential_num = 0

                for seq_num, week in enumerate(all_weeks, 1):
                    if seq_num > 53:
                        break
                    if week.start_date <= prop_date <= week.end_date:
                        week_found = week
                        sequential_num = seq_num
                        break

                if week_found and sequential_num > 0:
                    if sequential_num not in weekly_data:
                        weekly_data[sequential_num] = {
                            "count": 0,
                            "amount": 0.0,
                            "properties": []
                        }
                    weekly_data[sequential_num]["count"] += 1
                    weekly_data[sequential_num]["amount"] += prop.final_amount or 0.0
                    weekly_data[sequential_num]["properties"].append(prop.name)

                # Agrupar por CLUSTER
                if prop.condominium_worksite_id and prop.condominium_worksite_id.parent_id:
                    worksite = prop.condominium_worksite_id.parent_id
                    if worksite.parent_id:
                        cluster = worksite.parent_id
                        cluster_name = cluster.name
                    else:
                        cluster_name = worksite.name
                    
                    if cluster_name not in cluster_data:
                        cluster_data[cluster_name] = 0
                    cluster_data[cluster_name] += 1

            # Crear líneas de detalle por semana
            detail_lines = []
            for week_num, data in weekly_data.items():
                detail_lines.append((0, 0, {
                    "week_number": week_num,
                    "sold_count": data["count"],
                    "sold_amount": data["amount"],
                    "properties_list": ", ".join(data["properties"]),
                }))
            
            if detail_lines:
                record.week_detail_ids = detail_lines

            # Formatear weekly details (para vista texto)
            if weekly_data:
                lines = []
                for week_num in sorted(weekly_data.keys()):
                    data = weekly_data[week_num]
                    lines.append(f"S{week_num}: {data['count']} unidad{'es' if data['count'] > 1 else ''} - ${data['amount']:,.2f}")
                    lines.append(f"  Propiedades: {', '.join(data['properties'])}")
                    lines.append("")
                record.weekly_details = "\n".join(lines)
            else:
                record.weekly_details = "Sin ventas registradas"

            # Formatear cluster details
            if cluster_data:
                lines = []
                for cluster_name, count in cluster_data.items():
                    lines.append(f"{cluster_name}: {count} unidad{'es' if count > 1 else ''}")
                record.cluster_details = "\n".join(lines)
            else:
                record.cluster_details = "Sin datos"

            # Formatear properties list
            if sold_properties:
                prop_names = [prop.name for prop in sold_properties]
                record.properties_list = ", ".join(prop_names)
            else:
                record.properties_list = "Sin propiedades"

    def action_refresh(self):
        """Force recompute"""
        self._compute_totals()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Actualizado",
                "message": "Datos del gerente actualizados correctamente.",
                "type": "success",
                "sticky": False,
            },
        }