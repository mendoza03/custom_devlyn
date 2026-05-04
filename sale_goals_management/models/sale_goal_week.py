# -*- coding: utf-8 -*-

import math
from odoo import models, fields, api


class SaleGoalWeek(models.Model):
    _name = "sale.goal.week"
    _description = "Semana de Meta de Ventas"
    _order = "goal_id, period_id, week_number"
    
    goal_id = fields.Many2one(
        "sale.goal",
        string="Meta",
        required=True,
        ondelete="cascade",
    )
    
    period_id = fields.Many2one(
        "sale.goal.period",
        string="Período",
        required=True,
        ondelete="cascade",
    )
    
    calendar_week_id = fields.Many2one(
        "sale.goal.calendar.week",
        string="Semana del Calendario",
    )
    
    week_number = fields.Integer(
        string="Semana #",
        required=True,
    )
    
    week_name = fields.Char(
        string="Semana",
        compute="_compute_week_name",
        store=True,
    )
    
    start_date = fields.Date(
        string="Fecha Inicio",
        required=True,
    )
    
    end_date = fields.Date(
        string="Fecha Fin",
        required=True,
    )
    
    work_days = fields.Integer(
        string="Días Laborables",
        default=5,
    )
    
    weekly_amount = fields.Monetary(
        string="Importe Semanal",
        currency_field="currency_id",
        compute="_compute_weekly_amount",
        store=True,
    )
    
    currency_id = fields.Many2one(
        "res.currency",
        related="goal_id.currency_id",
        store=True,
    )
    
    weekly_leads = fields.Integer(
        string="Leads",
        compute="_compute_all_targets",
        store=True,
        readonly=False,
    )
    
    weekly_prospect = fields.Integer(
        string="Prospecto",
        compute="_compute_all_targets",
        store=True,
        readonly=False,
    )
    
    weekly_meeting = fields.Integer(
        string="Cita",
        compute="_compute_all_targets",
        store=True,
        readonly=False,
    )
    
    weekly_opportunity = fields.Integer(
        string="Oportunidad",
        compute="_compute_all_targets",
        store=True,
        readonly=False,
    )
    
    weekly_reserved = fields.Integer(
        string="Apartado",
        compute="_compute_all_targets",
        store=True,
        readonly=False,
    )
    
    weekly_closed = fields.Integer(
        string="Cierre",
        compute="_compute_all_targets",
        store=True,
        readonly=False,
    )
    
    daily_leads = fields.Integer(
        string="Leads/Día",
        compute="_compute_daily_targets",
        store=True,
    )
    
    daily_prospect = fields.Integer(
        string="Prospecto/Día",
        compute="_compute_daily_targets",
        store=True,
    )
    
    daily_meeting = fields.Integer(
        string="Cita/Día",
        compute="_compute_daily_targets",
        store=True,
    )
    
    daily_opportunity = fields.Integer(
        string="Oportunidad/Día",
        compute="_compute_daily_targets",
        store=True,
    )
    
    daily_reserved = fields.Integer(
        string="Apartado/Día",
        compute="_compute_daily_targets",
        store=True,
    )
    
    daily_closed = fields.Integer(
        string="Cierre/Día",
        compute="_compute_daily_targets",
        store=True,
    )

    daily_amount = fields.Monetary(
        string="Importe/Día",
        currency_field="currency_id",
        compute="_compute_daily_targets",
        store=True,
    )
    
    @api.depends("period_id.period_name", "week_number", "start_date", "end_date")
    def _compute_week_name(self):
        for record in self:
            if record.start_date and record.end_date:
                record.week_name = f"{record.period_id.period_name} - Semana {record.week_number} ({record.start_date.strftime('%d')}-{record.end_date.strftime('%d')})"
            else:
                record.week_name = f"{record.period_id.period_name} - Semana {record.week_number}"
    
    @api.depends("period_id.monthly_amount", "period_id.week_count")
    def _compute_weekly_amount(self):
        for record in self:
            if record.period_id and record.period_id.week_count > 0:
                record.weekly_amount = record.period_id.monthly_amount / record.period_id.week_count
            else:
                record.weekly_amount = 0
    
    @api.depends("period_id.monthly_leads", "period_id.week_count")
    def _compute_all_targets(self):
        for record in self:
            if not record.period_id or record.period_id.week_count == 0:
                record.weekly_leads = 0
                record.weekly_prospect = 0
                record.weekly_meeting = 0
                record.weekly_opportunity = 0
                record.weekly_reserved = 0
                record.weekly_closed = 0
                continue
            
            weeks_in_month = record.period_id.week_count
            
            record.weekly_leads = math.ceil(record.period_id.monthly_leads / weeks_in_month)
            record.weekly_prospect = math.ceil(record.period_id.monthly_prospect / weeks_in_month)
            record.weekly_meeting = math.ceil(record.period_id.monthly_meeting / weeks_in_month)
            record.weekly_opportunity = math.ceil(record.period_id.monthly_opportunity / weeks_in_month)
            record.weekly_reserved = math.ceil(record.period_id.monthly_reserved / weeks_in_month)
            record.weekly_closed = math.ceil(record.period_id.monthly_closed / weeks_in_month)
    
    @api.depends("weekly_leads", "weekly_prospect", "weekly_meeting", "weekly_opportunity",
                 "weekly_reserved", "weekly_closed", "weekly_amount", "work_days")
    def _compute_daily_targets(self):
        for record in self:
            if record.work_days == 0:
                record.daily_leads = 0
                record.daily_prospect = 0
                record.daily_meeting = 0
                record.daily_opportunity = 0
                record.daily_reserved = 0
                record.daily_closed = 0
                record.daily_amount = 0
                continue
            
            record.daily_leads = math.ceil(record.weekly_leads / record.work_days)
            record.daily_prospect = math.ceil(record.weekly_prospect / record.work_days)
            record.daily_meeting = math.ceil(record.weekly_meeting / record.work_days)
            record.daily_opportunity = math.ceil(record.weekly_opportunity / record.work_days)
            record.daily_reserved = math.ceil(record.weekly_reserved / record.work_days)
            record.daily_closed = math.ceil(record.weekly_closed / record.work_days)
            record.daily_amount = record.weekly_amount / record.work_days