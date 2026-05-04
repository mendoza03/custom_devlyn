# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime


class PropertySalesClusterSummary(models.Model):
    _name = "property.sales.cluster.summary"
    _description = "Property Sales Summary by Cluster (Consolidated)"
    _order = "cluster_id"

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
    )

    cluster_id = fields.Many2one(
        "project.worksite",
        string="Cluster",
        required=True,
    )

    cluster_name = fields.Char(
        string="Cluster",
        related="cluster_id.name",
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

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    # Totals (CONSOLIDADOS de todos los worksites del cluster)
    total_lots = fields.Integer(
        string="Total Lotes",
        compute="_compute_totals",
        store=True,
    )

    total_sold = fields.Integer(
        string="Total Apartado",
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
        string="%",
        compute="_compute_totals",
        store=True,
    )

    # Weekly fields - Units sold (53 weeks) - CONSOLIDADOS
    s1_sold = fields.Integer(string="S1", compute="_compute_weekly", store=True)
    s2_sold = fields.Integer(string="S2", compute="_compute_weekly", store=True)
    s3_sold = fields.Integer(string="S3", compute="_compute_weekly", store=True)
    s4_sold = fields.Integer(string="S4", compute="_compute_weekly", store=True)
    s5_sold = fields.Integer(string="S5", compute="_compute_weekly", store=True)
    s6_sold = fields.Integer(string="S6", compute="_compute_weekly", store=True)
    s7_sold = fields.Integer(string="S7", compute="_compute_weekly", store=True)
    s8_sold = fields.Integer(string="S8", compute="_compute_weekly", store=True)
    s9_sold = fields.Integer(string="S9", compute="_compute_weekly", store=True)
    s10_sold = fields.Integer(string="S10", compute="_compute_weekly", store=True)
    s11_sold = fields.Integer(string="S11", compute="_compute_weekly", store=True)
    s12_sold = fields.Integer(string="S12", compute="_compute_weekly", store=True)
    s13_sold = fields.Integer(string="S13", compute="_compute_weekly", store=True)
    s14_sold = fields.Integer(string="S14", compute="_compute_weekly", store=True)
    s15_sold = fields.Integer(string="S15", compute="_compute_weekly", store=True)
    s16_sold = fields.Integer(string="S16", compute="_compute_weekly", store=True)
    s17_sold = fields.Integer(string="S17", compute="_compute_weekly", store=True)
    s18_sold = fields.Integer(string="S18", compute="_compute_weekly", store=True)
    s19_sold = fields.Integer(string="S19", compute="_compute_weekly", store=True)
    s20_sold = fields.Integer(string="S20", compute="_compute_weekly", store=True)
    s21_sold = fields.Integer(string="S21", compute="_compute_weekly", store=True)
    s22_sold = fields.Integer(string="S22", compute="_compute_weekly", store=True)
    s23_sold = fields.Integer(string="S23", compute="_compute_weekly", store=True)
    s24_sold = fields.Integer(string="S24", compute="_compute_weekly", store=True)
    s25_sold = fields.Integer(string="S25", compute="_compute_weekly", store=True)
    s26_sold = fields.Integer(string="S26", compute="_compute_weekly", store=True)
    s27_sold = fields.Integer(string="S27", compute="_compute_weekly", store=True)
    s28_sold = fields.Integer(string="S28", compute="_compute_weekly", store=True)
    s29_sold = fields.Integer(string="S29", compute="_compute_weekly", store=True)
    s30_sold = fields.Integer(string="S30", compute="_compute_weekly", store=True)
    s31_sold = fields.Integer(string="S31", compute="_compute_weekly", store=True)
    s32_sold = fields.Integer(string="S32", compute="_compute_weekly", store=True)
    s33_sold = fields.Integer(string="S33", compute="_compute_weekly", store=True)
    s34_sold = fields.Integer(string="S34", compute="_compute_weekly", store=True)
    s35_sold = fields.Integer(string="S35", compute="_compute_weekly", store=True)
    s36_sold = fields.Integer(string="S36", compute="_compute_weekly", store=True)
    s37_sold = fields.Integer(string="S37", compute="_compute_weekly", store=True)
    s38_sold = fields.Integer(string="S38", compute="_compute_weekly", store=True)
    s39_sold = fields.Integer(string="S39", compute="_compute_weekly", store=True)
    s40_sold = fields.Integer(string="S40", compute="_compute_weekly", store=True)
    s41_sold = fields.Integer(string="S41", compute="_compute_weekly", store=True)
    s42_sold = fields.Integer(string="S42", compute="_compute_weekly", store=True)
    s43_sold = fields.Integer(string="S43", compute="_compute_weekly", store=True)
    s44_sold = fields.Integer(string="S44", compute="_compute_weekly", store=True)
    s45_sold = fields.Integer(string="S45", compute="_compute_weekly", store=True)
    s46_sold = fields.Integer(string="S46", compute="_compute_weekly", store=True)
    s47_sold = fields.Integer(string="S47", compute="_compute_weekly", store=True)
    s48_sold = fields.Integer(string="S48", compute="_compute_weekly", store=True)
    s49_sold = fields.Integer(string="S49", compute="_compute_weekly", store=True)
    s50_sold = fields.Integer(string="S50", compute="_compute_weekly", store=True)
    s51_sold = fields.Integer(string="S51", compute="_compute_weekly", store=True)
    s52_sold = fields.Integer(string="S52", compute="_compute_weekly", store=True)
    s53_sold = fields.Integer(string="S53", compute="_compute_weekly", store=True)

    # Weekly fields - Manager details (53 weeks) - CONSOLIDADOS
    s1_managers = fields.Text(string="Gerentes S1", compute="_compute_weekly", store=True)
    s2_managers = fields.Text(string="Gerentes S2", compute="_compute_weekly", store=True)
    s3_managers = fields.Text(string="Gerentes S3", compute="_compute_weekly", store=True)
    s4_managers = fields.Text(string="Gerentes S4", compute="_compute_weekly", store=True)
    s5_managers = fields.Text(string="Gerentes S5", compute="_compute_weekly", store=True)
    s6_managers = fields.Text(string="Gerentes S6", compute="_compute_weekly", store=True)
    s7_managers = fields.Text(string="Gerentes S7", compute="_compute_weekly", store=True)
    s8_managers = fields.Text(string="Gerentes S8", compute="_compute_weekly", store=True)
    s9_managers = fields.Text(string="Gerentes S9", compute="_compute_weekly", store=True)
    s10_managers = fields.Text(string="Gerentes S10", compute="_compute_weekly", store=True)
    s11_managers = fields.Text(string="Gerentes S11", compute="_compute_weekly", store=True)
    s12_managers = fields.Text(string="Gerentes S12", compute="_compute_weekly", store=True)
    s13_managers = fields.Text(string="Gerentes S13", compute="_compute_weekly", store=True)
    s14_managers = fields.Text(string="Gerentes S14", compute="_compute_weekly", store=True)
    s15_managers = fields.Text(string="Gerentes S15", compute="_compute_weekly", store=True)
    s16_managers = fields.Text(string="Gerentes S16", compute="_compute_weekly", store=True)
    s17_managers = fields.Text(string="Gerentes S17", compute="_compute_weekly", store=True)
    s18_managers = fields.Text(string="Gerentes S18", compute="_compute_weekly", store=True)
    s19_managers = fields.Text(string="Gerentes S19", compute="_compute_weekly", store=True)
    s20_managers = fields.Text(string="Gerentes S20", compute="_compute_weekly", store=True)
    s21_managers = fields.Text(string="Gerentes S21", compute="_compute_weekly", store=True)
    s22_managers = fields.Text(string="Gerentes S22", compute="_compute_weekly", store=True)
    s23_managers = fields.Text(string="Gerentes S23", compute="_compute_weekly", store=True)
    s24_managers = fields.Text(string="Gerentes S24", compute="_compute_weekly", store=True)
    s25_managers = fields.Text(string="Gerentes S25", compute="_compute_weekly", store=True)
    s26_managers = fields.Text(string="Gerentes S26", compute="_compute_weekly", store=True)
    s27_managers = fields.Text(string="Gerentes S27", compute="_compute_weekly", store=True)
    s28_managers = fields.Text(string="Gerentes S28", compute="_compute_weekly", store=True)
    s29_managers = fields.Text(string="Gerentes S29", compute="_compute_weekly", store=True)
    s30_managers = fields.Text(string="Gerentes S30", compute="_compute_weekly", store=True)
    s31_managers = fields.Text(string="Gerentes S31", compute="_compute_weekly", store=True)
    s32_managers = fields.Text(string="Gerentes S32", compute="_compute_weekly", store=True)
    s33_managers = fields.Text(string="Gerentes S33", compute="_compute_weekly", store=True)
    s34_managers = fields.Text(string="Gerentes S34", compute="_compute_weekly", store=True)
    s35_managers = fields.Text(string="Gerentes S35", compute="_compute_weekly", store=True)
    s36_managers = fields.Text(string="Gerentes S36", compute="_compute_weekly", store=True)
    s37_managers = fields.Text(string="Gerentes S37", compute="_compute_weekly", store=True)
    s38_managers = fields.Text(string="Gerentes S38", compute="_compute_weekly", store=True)
    s39_managers = fields.Text(string="Gerentes S39", compute="_compute_weekly", store=True)
    s40_managers = fields.Text(string="Gerentes S40", compute="_compute_weekly", store=True)
    s41_managers = fields.Text(string="Gerentes S41", compute="_compute_weekly", store=True)
    s42_managers = fields.Text(string="Gerentes S42", compute="_compute_weekly", store=True)
    s43_managers = fields.Text(string="Gerentes S43", compute="_compute_weekly", store=True)
    s44_managers = fields.Text(string="Gerentes S44", compute="_compute_weekly", store=True)
    s45_managers = fields.Text(string="Gerentes S45", compute="_compute_weekly", store=True)
    s46_managers = fields.Text(string="Gerentes S46", compute="_compute_weekly", store=True)
    s47_managers = fields.Text(string="Gerentes S47", compute="_compute_weekly", store=True)
    s48_managers = fields.Text(string="Gerentes S48", compute="_compute_weekly", store=True)
    s49_managers = fields.Text(string="Gerentes S49", compute="_compute_weekly", store=True)
    s50_managers = fields.Text(string="Gerentes S50", compute="_compute_weekly", store=True)
    s51_managers = fields.Text(string="Gerentes S51", compute="_compute_weekly", store=True)
    s52_managers = fields.Text(string="Gerentes S52", compute="_compute_weekly", store=True)
    s53_managers = fields.Text(string="Gerentes S53", compute="_compute_weekly", store=True)

    @api.depends("cluster_id", "calendar_id")
    def _compute_name(self):
        for record in self:
            if record.cluster_id and record.calendar_id:
                record.name = f"{record.cluster_id.name} - {record.calendar_id.name}"
            elif record.cluster_id:
                record.name = record.cluster_id.name
            else:
                record.name = "N/A"

    @api.depends("cluster_id")
    def _compute_totals(self):
        for record in self:
            if not record.cluster_id:
                record.total_lots = 0
                record.total_sold = 0
                record.sold_percentage = 0
                record.sold_percentage_display = "0.0%"
                continue

            # Obtener TODOS los worksites del cluster
            worksites = self.env["project.worksite"].search([
                ("parent_id", "=", record.cluster_id.id)
            ])

            if not worksites:
                record.total_lots = 0
                record.total_sold = 0
                record.sold_percentage = 0
                record.sold_percentage_display = "0.0%"
                continue

            # Obtener TODOS los condominiums de TODOS los worksites
            condominiums = self.env["condominium.worksite"].search([
                ("parent_id", "in", worksites.ids)
            ])

            if not condominiums:
                record.total_lots = 0
                record.total_sold = 0
                record.sold_percentage = 0
                record.sold_percentage_display = "0.0%"
                continue

            # Buscar TODOS los lotes de TODOS los condominiums
            domain = [
                ("is_property", "=", True),
                ("condominium_worksite_id", "in", condominiums.ids),
            ]

            total = self.env["product.template"].search_count(domain)
            sold = self.env["product.template"].search_count(
                domain + [("state", "=", "reserved")]
            )

            record.total_lots = total
            record.total_sold = sold
            record.sold_percentage = (sold / total * 100) if total > 0 else 0
            record.sold_percentage_display = f"{record.sold_percentage:.1f}%"

    @api.depends("cluster_id", "calendar_id")
    def _compute_weekly(self):
        for record in self:
            # Reset all weeks
            for i in range(1, 54):
                setattr(record, f"s{i}_sold", 0)
                setattr(record, f"s{i}_managers", "")

            if not record.cluster_id or not record.calendar_id:
                continue

            # Obtener TODOS los worksites del cluster
            worksites = self.env["project.worksite"].search([
                ("parent_id", "=", record.cluster_id.id)
            ])

            if not worksites:
                continue

            # Obtener TODOS los condominiums de TODOS los worksites
            condominiums = self.env["condominium.worksite"].search([
                ("parent_id", "in", worksites.ids)
            ])

            if not condominiums:
                continue

            # Obtener TODOS los meses del calendario
            calendar_months = self.env["sale.goal.calendar.month"].search([
                ("calendar_id", "=", record.calendar_id.id)
            ], order="month_number")

            if not calendar_months:
                continue

            # Obtener TODAS las semanas ordenadas
            all_weeks = []
            for month in calendar_months:
                month_weeks = self.env["sale.goal.calendar.week"].search([
                    ("month_id", "=", month.id)
                ], order="week_number")
                all_weeks.extend(month_weeks)

            # Base domain para TODOS los condominiums del cluster
            base_domain = [
                ("is_property", "=", True),
                ("condominium_worksite_id", "in", condominiums.ids),
                ("state", "=", "reserved"),
            ]

            # Calcular ventas CONSOLIDADAS por cada semana
            for sequential_num, week in enumerate(all_weeks, 1):
                if sequential_num > 53:
                    break

                start_dt = datetime.combine(week.start_date, datetime.min.time())
                end_dt = datetime.combine(week.end_date, datetime.max.time())

                # Buscar TODAS las propiedades vendidas en esta semana en TODO el cluster
                properties = self.env["product.template"].search(
                    base_domain + [
                        ("date_state_change", ">=", start_dt),
                        ("date_state_change", "<=", end_dt),
                    ]
                )

                count = len(properties)
                setattr(record, f"s{sequential_num}_sold", count)

                # Si hay ventas, agrupar por gerente (CONSOLIDADO de todas las obras)
                if count > 0:
                    manager_data = {}
                    
                    try:
                        for prop in properties:
                            if prop.gerente:
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
                        
                        # Formatear texto de gerentes
                        if manager_data:
                            lines = []
                            for data in manager_data.values():
                                lines.append(f"{data['name']}: {data['units']} unidad{'es' if data['units'] > 1 else ''} - ${data['amount']:,.2f}")
                                lines.append(f"  Propiedades: {', '.join(data['properties'])}")
                                lines.append("")
                            
                            setattr(record, f"s{sequential_num}_managers", "\n".join(lines))
                    except (KeyError, AttributeError):
                        pass

    def action_refresh(self):
        """Force recompute all summaries"""
        self._compute_totals()
        self._compute_weekly()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Actualizado",
                "message": "Datos del cluster actualizados correctamente.",
                "type": "success",
                "sticky": False,
            },
        }