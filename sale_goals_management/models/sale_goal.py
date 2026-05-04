# -*- coding: utf-8 -*-

import math
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleGoal(models.Model):
    _name = "sale.goal"
    _description = "Meta de Ventas"
    _order = "company_id, year desc, position, user_id"
    
    name = fields.Char(
        string="Nombre",
        compute="_compute_name",
        store=True,
    )
    
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    
    year = fields.Selection(
        selection="_get_years",
        string="Año",
        required=True,
        default=lambda self: str(fields.Date.today().year),
    )
    
    position = fields.Selection(
        selection=[
            ("cco", "CCO"),
            ("dvn", "DVN"),
            ("manager", "Gerente"),
            ("advisor", "Asesor"),
        ],
        string="Posición",
        required=True,
    )
    
    user_id = fields.Many2one(
        "res.users",
        string="Responsable",
        required=True,
        default=lambda self: self.env.user,
    )
    
    parent_id = fields.Many2one(
        "sale.goal",
        string="Meta Padre",
        domain="[('company_id', '=', company_id), ('year', '=', year)]",
    )
    
    annual_amount = fields.Monetary(
        string="Meta Anual",
        currency_field="currency_id",
        required=True,
    )
    
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("active", "Activa"),
            ("done", "Cerrada"),
        ],
        string="Estado",
        default="draft",
        required=True,
    )
    
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="company_id.currency_id",
        store=True,
    )
    
    period_ids = fields.One2many(
        "sale.goal.period",
        "goal_id",
        string="Períodos",
    )
    
    week_ids = fields.One2many(
        "sale.goal.week",
        "goal_id",
        string="Semanas",
    )
    
    child_ids = fields.One2many(
        "sale.goal",
        "parent_id",
        string="Metas Hijas",
    )
    
    child_count = fields.Integer(
        string="Cantidad de Metas Hijas",
        compute="_compute_child_count",
    )
    
    week_count = fields.Integer(
        string="Cantidad de Semanas",
        compute="_compute_week_count",
    )
    
    annual_units = fields.Integer(
        string="Unidades Anuales",
        compute="_compute_annual_targets",
        store=True,
    )
    
    annual_leads = fields.Integer(
        string="Leads Anuales",
        compute="_compute_annual_targets",
        store=True,
    )
    
    annual_prospect = fields.Integer(
        string="Prospectos Anuales",
        compute="_compute_annual_targets",
        store=True,
    )
    
    annual_meeting = fields.Integer(
        string="Citas Anuales",
        compute="_compute_annual_targets",
        store=True,
    )
    
    annual_opportunity = fields.Integer(
        string="Oportunidades Anuales",
        compute="_compute_annual_targets",
        store=True,
    )
    
    annual_reserved = fields.Integer(
        string="Apartados Anuales",
        compute="_compute_annual_targets",
        store=True,
    )
    
    annual_closed = fields.Integer(
        string="Cierres Anuales",
        compute="_compute_annual_targets",
        store=True,
    )
    
    @api.model
    def _get_years(self):
        current_year = fields.Date.today().year
        return [(str(year), str(year)) for year in range(current_year - 2, current_year + 5)]
    
    @api.depends("company_id", "year", "position", "user_id")
    def _compute_name(self):
        for record in self:
            position_name = dict(self._fields["position"].selection).get(record.position, "")
            user_name = record.user_id.name or ""
            record.name = f"{record.company_id.name} - {record.year} - {position_name} {user_name}"
    
    @api.depends("child_ids")
    def _compute_child_count(self):
        for record in self:
            record.child_count = len(record.child_ids)
    
    @api.depends("week_ids")
    def _compute_week_count(self):
        for record in self:
            record.week_count = len(record.week_ids)
    
    @api.depends("annual_amount")
    def _compute_annual_targets(self):
        config = self.env["sale.goal.config"].get_config()
        
        for record in self:
            if not record.annual_amount or not config.average_unit_price:
                record.annual_units = 0
                record.annual_leads = 0
                record.annual_prospect = 0
                record.annual_meeting = 0
                record.annual_opportunity = 0
                record.annual_reserved = 0
                record.annual_closed = 0
                continue
            
            units = record.annual_amount / config.average_unit_price
            record.annual_units = math.ceil(units)
            
            leads = record.annual_units * config.leads_per_unit
            record.annual_leads = math.ceil(leads)
            
            prospect = record.annual_leads * (config.prospect_rate / 100)
            record.annual_prospect = math.ceil(prospect)
            
            meeting = record.annual_prospect * (config.meeting_rate / 100)
            record.annual_meeting = math.ceil(meeting)
            
            opportunity = record.annual_meeting * (config.opportunity_rate / 100)
            record.annual_opportunity = math.ceil(opportunity)
            
            reserved = record.annual_opportunity * (config.reserved_rate / 100)
            record.annual_reserved = math.ceil(reserved)
            
            closed = record.annual_reserved * (config.closed_rate / 100)
            record.annual_closed = math.ceil(closed)
    
    @api.constrains("company_id", "year", "user_id")
    def _check_unique_goal(self):
        for record in self:
            domain = [
                ("company_id", "=", record.company_id.id),
                ("year", "=", record.year),
                ("user_id", "=", record.user_id.id),
                ("id", "!=", record.id),
            ]
            if self.search_count(domain) > 0:
                raise ValidationError(
                    f"Ya existe una meta para {record.user_id.name} "
                    f"en {record.company_id.name} para el año {record.year}"
                )
    
    def action_generate_periods(self):
        self.ensure_one()
        
        if self.period_ids:
            raise ValidationError("Los períodos ya han sido generados para esta meta.")
        
        # Buscar calendario activo para el año y empresa
        calendar = self.env["sale.goal.calendar"].search([
            ("year", "=", self.year),
            ("state", "=", "active"),
            "|",
            ("company_id", "=", self.company_id.id),
            ("company_id", "=", False),
        ], limit=1)
        
        # LOG DE DEPURACIÓN
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning(f"=== DEBUG CALENDARIO ===")
        _logger.warning(f"Buscando calendario para año: {self.year}, empresa: {self.company_id.name}")
        _logger.warning(f"Calendario encontrado: {calendar.name if calendar else 'NINGUNO'}")
        if calendar:
            _logger.warning(f"Meses en calendario: {len(calendar.month_ids)}")
            for month in calendar.month_ids:
                _logger.warning(f"  Mes {month.month_number}: {len(month.week_ids)} semanas")
                for week in month.week_ids:
                    _logger.warning(f"    Semana {week.week_number}: {week.start_date} - {week.end_date}")
        
        # Validar que exista un calendario configurado
        if not calendar:
            raise ValidationError(
                f"No se encontró un calendario activo para el año {self.year}.\n\n"
                f"Por favor:\n"
                f"1. Vaya a Configuración > Metas de Ventas\n"
                f"2. Cree un calendario para el año {self.year}\n"
                f"3. Genere los meses y semanas\n"
                f"4. Active el calendario\n"
                f"5. Vuelva a intentar generar los períodos"
            )
        
        # Validar que el calendario tenga meses con semanas generadas
        if not calendar.month_ids:
            raise ValidationError(
                f"El calendario '{calendar.name}' no tiene meses generados.\n\n"
                f"Por favor:\n"
                f"1. Abra el calendario desde Configuración > Metas de Ventas\n"
                f"2. Haga clic en 'Generar Meses'\n"
                f"3. Haga clic en 'Generar Semanas'\n"
                f"4. Vuelva a intentar generar los períodos"
            )
        
        # Validar que al menos un mes tenga semanas
        months_with_weeks = calendar.month_ids.filtered(lambda m: m.week_ids)
        if not months_with_weeks:
            raise ValidationError(
                f"El calendario '{calendar.name}' no tiene semanas generadas en ningún mes.\n\n"
                f"Por favor:\n"
                f"1. Abra el calendario desde Configuración > Metas de Ventas\n"
                f"2. Haga clic en 'Generar Semanas'\n"
                f"3. Vuelva a intentar generar los períodos"
            )
        
        # Crear períodos mensuales
        monthly_amount = self.annual_amount / 12
        
        for month in range(1, 13):
            self.env["sale.goal.period"].create({
                "goal_id": self.id,
                "period_number": month,
                "monthly_amount": monthly_amount,
            })
        
        # Generar semanas desde el calendario
        self._generate_weeks_from_calendar(calendar)
        
        self.state = "active"
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Períodos y Semanas Generados",
                "message": f"Se han generado 12 períodos mensuales y {len(self.week_ids)} semanas desde el calendario '{calendar.name}'.",
                "type": "success",
                "sticky": False,
            },
        }
    
    def _generate_weeks_from_calendar(self, calendar):
        """Genera semanas desde el calendario configurado"""
        missing_months = []
        
        for period in self.period_ids:
            calendar_month = calendar.month_ids.filtered(
                lambda m: m.month_number == period.period_number
            )
            
            # Verificar que el mes exista y tenga semanas
            if not calendar_month:
                missing_months.append(period.period_name)
                continue
            
            if not calendar_month.week_ids:
                missing_months.append(period.period_name)
                continue
            
            # Crear semanas desde el calendario
            for cal_week in calendar_month.week_ids:
                self.env["sale.goal.week"].create({
                    "goal_id": self.id,
                    "period_id": period.id,
                    "calendar_week_id": cal_week.id,
                    "week_number": cal_week.week_number,
                    "start_date": cal_week.start_date,
                    "end_date": cal_week.end_date,
                    "work_days": cal_week.work_days,
                })
        
        # Si hay meses sin semanas, lanzar error
        if missing_months:
            raise ValidationError(
                f"El calendario '{calendar.name}' no tiene semanas configuradas para los siguientes meses:\n\n"
                f"{', '.join(missing_months)}\n\n"
                f"Por favor complete el calendario antes de generar períodos."
            )
    
    def action_recalculate(self):
        self.ensure_one()

        # 1. Recalcular targets anuales
        self._compute_annual_targets()
        self.invalidate_recordset()
        self.flush_recordset()

        # 2. Redistribuir monthly_amount en cada periodo y recalcular
        if self.period_ids:
            monthly_amount = self.annual_amount / 12
            for period in self.period_ids:
                period.write({"monthly_amount": monthly_amount})
            self.period_ids.invalidate_recordset()
            self.period_ids.flush_recordset()
            for period in self.period_ids:
                period._compute_all_targets()
            self.period_ids.invalidate_recordset()
            self.period_ids.flush_recordset()

        # 3. Recalcular semanas
        if self.week_ids:
            for week in self.week_ids:
                week._compute_all_targets()
                week._compute_weekly_amount()
                week._compute_daily_targets()
            self.week_ids.invalidate_recordset()
            self.week_ids.flush_recordset()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Recalculado",
                "message": "Todas las metas han sido recalculadas.",
                "type": "success",
                "sticky": False,
            },
        }
    
    def action_close(self):
        self.ensure_one()
        self.state = "done"
    
    def action_open_parent(self):
        self.ensure_one()
        if not self.parent_id:
            return
        
        return {
            "type": "ir.actions.act_window",
            "name": "Meta Padre",
            "res_model": "sale.goal",
            "res_id": self.parent_id.id,
            "view_mode": "form",
            "target": "current",
        }
    
    def action_open_children(self):
        self.ensure_one()
        
        return {
            "type": "ir.actions.act_window",
            "name": "Metas Hijas",
            "res_model": "sale.goal",
            "domain": [("parent_id", "=", self.id)],
            "view_mode": "list,form",
            "target": "current",
        }