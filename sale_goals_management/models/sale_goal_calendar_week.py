# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleGoalCalendarWeek(models.Model):
    _name = "sale.goal.calendar.week"
    _description = "Semana del Calendario de Metas"
    _order = "month_id, week_number"
    
    month_id = fields.Many2one(
        "sale.goal.calendar.month",
        string="Mes",
        required=True,
        ondelete="cascade",
    )
    
    week_number = fields.Integer(
        string="Semana #",
        default=1,
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
        required=True,
    )
    
    @api.depends("month_id.month_name", "week_number", "start_date", "end_date")
    def _compute_week_name(self):
        for record in self:
            if record.start_date and record.end_date:
                record.week_name = f"{record.month_id.month_name} - Semana {record.week_number} ({record.start_date.strftime('%d')}-{record.end_date.strftime('%d')})"
            else:
                record.week_name = f"{record.month_id.month_name} - Semana {record.week_number}"