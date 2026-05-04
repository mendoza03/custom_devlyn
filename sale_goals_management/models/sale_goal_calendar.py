# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, timedelta


class SaleGoalCalendar(models.Model):
    _name = "sale.goal.calendar"
    _description = "Calendario Anual de Metas"
    _order = "year desc, company_id"
    
    name = fields.Char(
        string="Nombre",
        compute="_compute_name",
        store=True,
    )
    
    config_id = fields.Many2one(
        "sale.goal.config",
        string="Configuración",
        required=True,
        ondelete="cascade",
    )
    
    year = fields.Selection(
        selection="_get_years",
        string="Año",
        required=True,
    )
    
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
    )
    
    month_ids = fields.One2many(
        "sale.goal.calendar.month",
        "calendar_id",
        string="Meses",
    )
    
    total_weeks = fields.Integer(
        string="Total Semanas",
        compute="_compute_total_weeks",
        store=True,
    )
    
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("active", "Activo"),
        ],
        string="Estado",
        default="draft",
    )
    
    @api.model
    def _get_years(self):
        current_year = fields.Date.today().year
        return [(str(year), str(year)) for year in range(current_year - 2, current_year + 10)]
    
    @api.depends("year", "company_id")
    def _compute_name(self):
        for record in self:
            company_name = record.company_id.name if record.company_id else "General"
            record.name = f"Calendario {record.year} - {company_name}"
    
    @api.depends("month_ids.week_count")
    def _compute_total_weeks(self):
        for record in self:
            record.total_weeks = sum(record.month_ids.mapped("week_count"))
    
    def action_generate_months(self):
        self.ensure_one()
        
        if self.month_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Error",
                    "message": "Los meses ya han sido generados para este calendario.",
                    "type": "warning",
                    "sticky": False,
                },
            }
        
        year_int = int(self.year)
        
        for month in range(1, 13):
            first_day = date(year_int, month, 1)
            
            if month == 12:
                last_day = date(year_int, 12, 31)
            else:
                last_day = date(year_int, month + 1, 1) - timedelta(days=1)
            
            days_in_month = (last_day - first_day).days + 1
            week_count = (days_in_month + 6) // 7
            
            self.env["sale.goal.calendar.month"].create({
                "calendar_id": self.id,
                "month_number": month,
                "week_count": week_count,
            })
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Meses Generados",
                "message": "Se han generado 12 meses exitosamente.",
                "type": "success",
                "sticky": False,
            },
        }
    
    def action_generate_weeks(self):
        self.ensure_one()
        
        for month in self.month_ids:
            month.action_generate_weeks()
        
        self.state = "active"
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Semanas Generadas",
                "message": f"Se han generado {self.total_weeks} semanas para todos los meses.",
                "type": "success",
                "sticky": False,
            },
        }