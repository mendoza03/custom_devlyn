# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class PropertySalesWeekSummary(models.Model):
    _name = "property.sales.week.summary"
    _description = "Property Sales Summary by Week"
    _order = "week_number"

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

    week_number = fields.Integer(
        string="Semana",
        required=True,
    )

    week_number_str = fields.Char(
        string="Semana Nº",
        compute="_compute_week_number_str",
        store=True,
    )

    week_start = fields.Date(
        string="Inicio",
        required=True,
    )

    week_end = fields.Date(
        string="Fin",
        required=True,
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    # Totals
    total_lots = fields.Integer(
        string="Total Lotes",
        compute="_compute_totals",
        store=True,
    )

    total_sold = fields.Integer(
        string="Vendido en Semana",
        compute="_compute_totals",
        store=True,
    )

    sold_percentage = fields.Float(
        string="% Apartado",
        compute="_compute_totals",
        store=True,
        digits=(5, 1),
    )

    sold_percentage_display = fields.Char(
        string="% Apartado",
        compute="_compute_totals",
        store=True,
    )

    # Clusters (Many2many relational)
    cluster_ids = fields.Many2many(
        "project.worksite",
        string="Clusters con Ventas",
        compute="_compute_totals",
        store=True,
    )

    # Cluster breakdown (para mostrar cantidades)
    cluster_details = fields.Text(
        string="Detalle por Cluster",
        compute="_compute_totals",
        store=True,
    )

    # Manager breakdown
    manager_details = fields.Text(
        string="Detalle por Gerente",
        compute="_compute_totals",
        store=True,
    )

    # Líneas de resumen consolidado por cluster
    cluster_summary_ids = fields.One2many(
        "property.sales.week.cluster.summary",
        "week_id",
        string="Resumen por Cluster",
    )

    # Líneas de detalle por cluster/worksite
    cluster_detail_ids = fields.One2many(
        "property.sales.week.cluster.detail",
        "week_id",
        string="Detalle por Cluster/Obra",
    )

    # NUEVO: Líneas de detalle por propiedad vendida
    property_detail_ids = fields.One2many(
        "property.sales.week.property.detail",
        "week_id",
        string="Detalle por Propiedades",
    )

    # Campos para Dashboard Ninja - Obras
    has_estepa = fields.Boolean(
        string="Estepa Activo",
        compute="_compute_worksites",
        store=True,
    )
    
    has_desierto = fields.Boolean(
        string="Desierto Activo",
        compute="_compute_worksites",
        store=True,
    )
    
    has_sabana = fields.Boolean(
        string="Sabana Activo",
        compute="_compute_worksites",
        store=True,
    )
    
    has_tundra = fields.Boolean(
        string="Tundra Activo",
        compute="_compute_worksites",
        store=True,
    )
    
    worksites_list = fields.Char(
        string="Obras",
        compute="_compute_worksites",
        store=True,
    )

    @api.depends("week_number")
    def _compute_name(self):
        for record in self:
            if record.week_number:
                record.name = f"S{record.week_number}"
            else:
                record.name = "N/A"

    @api.depends("week_number")
    def _compute_week_number_str(self):
        for record in self:
            record.week_number_str = str(record.week_number) if record.week_number else "0"

    @api.depends("calendar_id", "week_start", "week_end")
    def _compute_totals(self):
        for record in self:
            # NO limpiar líneas existentes - solo actualizar
            
            if not record.calendar_id or not record.week_start or not record.week_end:
                record.total_lots = 0
                record.total_sold = 0
                record.sold_percentage = 0
                record.sold_percentage_display = "0.0%"
                record.cluster_ids = [(5, 0, 0)]
                record.cluster_details = ""
                record.manager_details = ""
                continue

            # Obtener TODOS los lotes del sistema
            all_properties = self.env["product.template"].search([
                ("is_property", "=", True),
            ])
            
            record.total_lots = len(all_properties)

            # Obtener propiedades apartadas EN ESTA SEMANA
            start_dt = datetime.combine(record.week_start, datetime.min.time())
            end_dt = datetime.combine(record.week_end, datetime.max.time())

            sold_properties = self.env["product.template"].search([
                ("is_property", "=", True),
                ("state", "=", "reserved"),
                ("date_state_change", ">=", start_dt),
                ("date_state_change", "<=", end_dt),
            ])

            record.total_sold = len(sold_properties)
            record.sold_percentage = (record.total_sold / record.total_lots * 100) if record.total_lots > 0 else 0
            record.sold_percentage_display = f"{record.sold_percentage:.1f}%"

            # Obtener TODOS los gerentes válidos (empleados que existen actualmente)
            valid_managers = self.env["hr.employee"].search([
                ("active", "=", True),
            ])
            valid_manager_ids = set(valid_managers.ids)

            # Agrupar ventas por cluster y worksite
            sales_by_cluster_worksite = {}
            manager_data = {}
            cluster_ids_set = set()

            for prop in sold_properties:
                # Obtener cluster y worksite
                if prop.condominium_worksite_id and prop.condominium_worksite_id.parent_id:
                    worksite = prop.condominium_worksite_id.parent_id
                    if worksite.parent_id:
                        cluster = worksite.parent_id
                        cluster_id = cluster.id
                        cluster_name = cluster.name
                    else:
                        cluster = worksite
                        cluster_id = worksite.id
                        cluster_name = worksite.name
                    
                    worksite_id = worksite.id
                    worksite_name = worksite.name
                    
                    cluster_ids_set.add(cluster_id)
                    
                    # Crear clave única cluster+worksite
                    key = (cluster_id, worksite_id)
                    
                    if key not in sales_by_cluster_worksite:
                        sales_by_cluster_worksite[key] = {
                            "cluster_id": cluster_id,
                            "cluster_name": cluster_name,
                            "worksite_id": worksite_id,
                            "worksite_name": worksite_name,
                            "count": 0,
                            "amount": 0.0,
                        }
                    sales_by_cluster_worksite[key]["count"] += 1
                    sales_by_cluster_worksite[key]["amount"] += prop.final_amount or 0.0

                # Agrupar por GERENTE (solo gerentes válidos - hr.employee)
                try:
                    if prop.gerente and prop.gerente.id in valid_manager_ids:
                        manager_id = prop.gerente.id
                        manager_name = prop.gerente.name
                        
                        if manager_id not in manager_data:
                            manager_data[manager_id] = {
                                "name": manager_name,
                                "units": 0,
                                "amount": 0.0,
                                "properties": []
                            }
                        
                        manager_data[manager_id]["units"] += 1
                        manager_data[manager_id]["amount"] += prop.final_amount or 0.0
                        manager_data[manager_id]["properties"].append(prop.name)
                except (KeyError, AttributeError):
                    pass

            # ACTUALIZAR líneas de DETALLE existentes (no crear nuevas)
            for line in record.cluster_detail_ids:
                key = (line.cluster_id.id, line.worksite_id.id)
                
                if key in sales_by_cluster_worksite:
                    # Hay ventas - actualizar
                    line.write({
                        "sold_count": sales_by_cluster_worksite[key]["count"],
                        "sold_amount": sales_by_cluster_worksite[key]["amount"],
                    })
                else:
                    # No hay ventas - dejar en 0
                    line.write({
                        "sold_count": 0,
                        "sold_amount": 0.0,
                    })

            # ACTUALIZAR líneas de RESUMEN CONSOLIDADO
            cluster_totals = {}
            for line in record.cluster_detail_ids:
                cluster_id = line.cluster_id.id
                if cluster_id not in cluster_totals:
                    cluster_totals[cluster_id] = {
                        "sold_count": 0,
                        "sold_amount": 0.0,
                    }
                cluster_totals[cluster_id]["sold_count"] += line.sold_count
                cluster_totals[cluster_id]["sold_amount"] += line.sold_amount

            # Actualizar líneas de resumen consolidado
            for summary_line in record.cluster_summary_ids:
                cluster_id = summary_line.cluster_id.id
                if cluster_id in cluster_totals:
                    summary_line.write({
                        "sold_count": cluster_totals[cluster_id]["sold_count"],
                        "sold_amount": cluster_totals[cluster_id]["sold_amount"],
                    })
                else:
                    summary_line.write({
                        "sold_count": 0,
                        "sold_amount": 0.0,
                    })

            # NUEVO: CREAR/ACTUALIZAR líneas de detalle por PROPIEDAD
            # Primero, limpiar líneas existentes
            record.property_detail_ids.unlink()
            
            # Crear una línea por cada propiedad vendida esta semana
            property_lines = []
            for prop in sold_properties:
                # Obtener cluster y worksite
                cluster_id = False
                worksite_id = False
                
                if prop.condominium_worksite_id and prop.condominium_worksite_id.parent_id:
                    worksite = prop.condominium_worksite_id.parent_id
                    worksite_id = worksite.id
                    
                    if worksite.parent_id:
                        cluster = worksite.parent_id
                        cluster_id = cluster.id
                    else:
                        cluster_id = worksite.id
                
                # Obtener gerente SOLO si es válido (hr.employee)
                manager_id = False
                try:
                    if prop.gerente and prop.gerente.id in valid_manager_ids:
                        manager_id = prop.gerente.id
                except (KeyError, AttributeError):
                    pass
                
                property_lines.append((0, 0, {
                    "property_id": prop.id,
                    "manager_id": manager_id if manager_id else False,
                    "cluster_id": cluster_id if cluster_id else False,
                    "worksite_id": worksite_id if worksite_id else False,
                    "sold_amount": prop.final_amount or 0.0,
                }))
            
            if property_lines:
                record.property_detail_ids = property_lines

            # Asignar Many2many de clusters
            if cluster_ids_set:
                record.cluster_ids = [(6, 0, list(cluster_ids_set))]
            else:
                record.cluster_ids = [(5, 0, 0)]

            # Formatear cluster details (para vista texto)
            if sales_by_cluster_worksite:
                lines = []
                for data in sales_by_cluster_worksite.values():
                    lines.append(f"{data['cluster_name']} - {data['worksite_name']}: {data['count']} unidad{'es' if data['count'] > 1 else ''}")
                record.cluster_details = "\n".join(lines)
            else:
                record.cluster_details = "Sin ventas"

            # Formatear manager details
            if manager_data:
                lines = []
                for data in manager_data.values():
                    lines.append(f"{data['name']}: {data['units']} unidad{'es' if data['units'] > 1 else ''} - ${data['amount']:,.2f}")
                    lines.append(f"  Propiedades: {', '.join(data['properties'])}")
                    lines.append("")
                record.manager_details = "\n".join(lines)
            else:
                record.manager_details = "Sin ventas"

    @api.depends("cluster_detail_ids", "cluster_detail_ids.worksite_id")
    def _compute_worksites(self):
        """Identifica qué obras tuvieron ventas"""
        for record in self:
            worksite_names = []
            has_estepa = False
            has_desierto = False
            has_sabana = False
            has_tundra = False
            
            # Revisar líneas de detalle
            for line in record.cluster_detail_ids:
                if line.worksite_id:
                    worksite_name = line.worksite_id.name
                    worksite_names.append(worksite_name)
                    
                    # Detectar obra específica
                    name_lower = worksite_name.lower()
                    if "estepa" in name_lower:
                        has_estepa = True
                    elif "desierto" in name_lower:
                        has_desierto = True
                    elif "sabana" in name_lower:
                        has_sabana = True
                    elif "tundra" in name_lower:
                        has_tundra = True
            
            # Asignar valores
            record.has_estepa = has_estepa
            record.has_desierto = has_desierto
            record.has_sabana = has_sabana
            record.has_tundra = has_tundra
            record.worksites_list = ", ".join(worksite_names) if worksite_names else "Sin obras"

    def action_refresh(self):
        """Force recompute"""
        self._compute_totals()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Actualizado",
                "message": "Datos de la semana actualizados correctamente.",
                "type": "success",
                "sticky": False,
            },
        }