# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, timedelta


class SaleGoalCalendarMonth(models.Model):
    _name = "sale.goal.calendar.month"
    _description = "Mes del Calendario de Metas"
    _order = "calendar_id, month_number"
    _rec_name = "month_name"
    
    calendar_id = fields.Many2one(
        "sale.goal.calendar",
        string="Calendario",
        required=True,
        ondelete="cascade",
    )
    
    month_number = fields.Integer(
        string="Número de Mes",
        required=True,
    )
    
    month_name = fields.Char(
        string="Mes",
        compute="_compute_month_name",
        store=True,
    )
    
    week_count = fields.Integer(
        string="Cantidad de Semanas",
        default=4,
        required=True,
    )
    
    week_ids = fields.One2many(
        "sale.goal.calendar.week",
        "month_id",
        string="Semanas",
    )
    
    @api.depends("month_number", "calendar_id.year")
    def _compute_month_name(self):
        months = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        
        for record in self:
            month_name = months.get(record.month_number, "")
            year = record.calendar_id.year or ""
            record.month_name = f"{month_name} {year}"
    
    def action_generate_weeks(self):
        self.ensure_one()
        
        if self.week_ids:
            return
        
        year_int = int(self.calendar_id.year)
        month = self.month_number
        
        # Primer y último día del mes
        first_day = date(year_int, month, 1)
        if month == 12:
            last_day = date(year_int, 12, 31)
        else:
            last_day = date(year_int, month + 1, 1) - timedelta(days=1)
        
        week_number = 1
        current_date = first_day
        
        while current_date <= last_day:
            # Primera semana: desde el día 1 hasta el primer domingo
            if week_number == 1:
                # Encontrar el primer domingo
                days_until_sunday = (6 - current_date.weekday()) % 7
                week_end = current_date + timedelta(days=days_until_sunday)
                
                # No pasar del último día del mes
                if week_end > last_day:
                    week_end = last_day
            else:
                # Semanas subsecuentes: lunes a domingo (7 días)
                week_end = current_date + timedelta(days=6)
                
                # No pasar del último día del mes
                if week_end > last_day:
                    week_end = last_day
            
            # Calcular días laborables (lunes a viernes)
            work_days = 0
            temp_date = current_date
            while temp_date <= week_end:
                if temp_date.weekday() < 5:  # 0=Lunes, 4=Viernes
                    work_days += 1
                temp_date += timedelta(days=1)
            
            # Crear la semana
            self.env["sale.goal.calendar.week"].create({
                "month_id": self.id,
                "week_number": week_number,
                "start_date": current_date,
                "end_date": week_end,
                "work_days": work_days,
            })
            
            # Avanzar al siguiente lunes
            current_date = week_end + timedelta(days=1)
            week_number += 1