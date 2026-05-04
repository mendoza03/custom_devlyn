# -*- coding: utf-8 -*-

import math
from odoo import models, fields, api


class SaleGoalPeriod(models.Model):
    _name = "sale.goal.period"
    _description = "Período de Meta de Ventas"
    _order = "goal_id, period_number"
    
    goal_id = fields.Many2one(
        "sale.goal",
        string="Meta",
        required=True,
        ondelete="cascade",
    )
    
    period_number = fields.Integer(
        string="Número de Período",
        required=True,
    )
    
    period_name = fields.Char(
        string="Período",
        compute="_compute_period_name",
        store=True,
    )
    
    monthly_amount = fields.Monetary(
        string="Importe Mensual",
        currency_field="currency_id",
        required=True,
    )
    
    currency_id = fields.Many2one(
        "res.currency",
        related="goal_id.currency_id",
        store=True,
    )
    
    week_ids = fields.One2many(
        "sale.goal.week",
        "period_id",
        string="Semanas",
    )
    
    week_count = fields.Integer(
        string="Cantidad de Semanas",
        compute="_compute_week_count",
    )
    
    # CAMPOS MENSUALES
    monthly_units = fields.Integer(
        string="Unidades",
        compute="_compute_all_targets",
        store=True,
    )
    
    monthly_leads = fields.Integer(
        string="Leads",
        compute="_compute_all_targets",
        store=True,
    )
    
    monthly_prospect = fields.Integer(
        string="Prospecto",
        compute="_compute_all_targets",
        store=True,
    )
    
    monthly_meeting = fields.Integer(
        string="Cita",
        compute="_compute_all_targets",
        store=True,
    )
    
    monthly_opportunity = fields.Integer(
        string="Oportunidad",
        compute="_compute_all_targets",
        store=True,
    )
    
    monthly_reserved = fields.Integer(
        string="Apartado",
        compute="_compute_all_targets",
        store=True,
    )
    
    monthly_closed = fields.Integer(
        string="Cierre",
        compute="_compute_all_targets",
        store=True,
    )
    
    @api.depends("period_number", "goal_id.year")
    def _compute_period_name(self):
        """Genera el nombre del período"""
        months = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        
        for record in self:
            month_name = months.get(record.period_number, "")
            year = record.goal_id.year or ""
            record.period_name = f"{month_name} {year}"
    
    @api.depends("week_ids")
    def _compute_week_count(self):
        """Cuenta las semanas del mes"""
        for record in self:
            record.week_count = len(record.week_ids)
    
    @api.depends("monthly_amount", "goal_id.annual_leads")
    def _compute_all_targets(self):
        """Calcula todas las metas mensuales"""
        config = self.env["sale.goal.config"].get_config()
        
        for record in self:
            if not record.monthly_amount or not config.average_unit_price:
                record.monthly_units = 0
                record.monthly_leads = 0
                record.monthly_prospect = 0
                record.monthly_meeting = 0
                record.monthly_opportunity = 0
                record.monthly_reserved = 0
                record.monthly_closed = 0
                continue
            
            # Calcular desde los leads anuales distribuidos
            if record.goal_id.annual_leads > 0:
                # Distribución proporcional basada en el importe
                proportion = record.monthly_amount / record.goal_id.annual_amount if record.goal_id.annual_amount else 0
                
                record.monthly_leads = math.ceil(record.goal_id.annual_leads * proportion)
                record.monthly_prospect = math.ceil(record.goal_id.annual_prospect * proportion)
                record.monthly_meeting = math.ceil(record.goal_id.annual_meeting * proportion)
                record.monthly_opportunity = math.ceil(record.goal_id.annual_opportunity * proportion)
                record.monthly_reserved = math.ceil(record.goal_id.annual_reserved * proportion)
                record.monthly_closed = math.ceil(record.goal_id.annual_closed * proportion)
                
                # Calcular unidades desde el importe
                units = record.monthly_amount / config.average_unit_price
                record.monthly_units = math.ceil(units)
            else:
                # Fallback: calcular desde unidades
                units = record.monthly_amount / config.average_unit_price
                record.monthly_units = math.ceil(units)
                
                leads = record.monthly_units * config.leads_per_unit
                record.monthly_leads = math.ceil(leads)
                
                prospect = record.monthly_leads * (config.prospect_rate / 100)
                record.monthly_prospect = math.ceil(prospect)
                
                meeting = record.monthly_prospect * (config.meeting_rate / 100)
                record.monthly_meeting = math.ceil(meeting)
                
                opportunity = record.monthly_meeting * (config.opportunity_rate / 100)
                record.monthly_opportunity = math.ceil(opportunity)
                
                reserved = record.monthly_opportunity * (config.reserved_rate / 100)
                record.monthly_reserved = math.ceil(reserved)
                
                closed = record.monthly_reserved * (config.closed_rate / 100)
                record.monthly_closed = math.ceil(closed)