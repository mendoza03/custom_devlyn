# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleGoalWeekCRMIntegration(models.Model):
    _inherit = "sale.goal.week"
    
    actual_leads = fields.Integer(
        string="Leads Reales",
        compute="_compute_actual_metrics",
    )
    
    actual_prospect = fields.Integer(
        string="Prospectos Reales",
        compute="_compute_actual_metrics",
    )
    
    actual_meeting = fields.Integer(
        string="Citas Reales",
        compute="_compute_actual_metrics",
    )
    
    actual_opportunity = fields.Integer(
        string="Oportunidades Reales",
        compute="_compute_actual_metrics",
    )
    
    actual_reserved = fields.Integer(
        string="Apartados Reales",
        compute="_compute_actual_metrics",
    )
    
    actual_closed = fields.Integer(
        string="Cierres Reales",
        compute="_compute_actual_metrics",
    )
    
    actual_revenue = fields.Monetary(
        string="Ingreso Esperado Real",
        currency_field="currency_id",
        compute="_compute_actual_metrics",
    )
    
    # Campos ESPEJO con store=True - Para Dashboard Ninja (ocultos en vistas)
    actual_leads_stored = fields.Integer(
        string="Leads Reales (Stored)",
        compute="_compute_actual_metrics",
        store=True,
    )
    
    actual_prospect_stored = fields.Integer(
        string="Prospectos Reales (Stored)",
        compute="_compute_actual_metrics",
        store=True,
    )
    
    actual_meeting_stored = fields.Integer(
        string="Citas Reales (Stored)",
        compute="_compute_actual_metrics",
        store=True,
    )
    
    actual_opportunity_stored = fields.Integer(
        string="Oportunidades Reales (Stored)",
        compute="_compute_actual_metrics",
        store=True,
    )
    
    actual_reserved_stored = fields.Integer(
        string="Apartados Reales (Stored)",
        compute="_compute_actual_metrics",
        store=True,
    )
    
    actual_closed_stored = fields.Integer(
        string="Cierres Reales (Stored)",
        compute="_compute_actual_metrics",
        store=True,
    )
    
    actual_revenue_stored = fields.Monetary(
        string="Ingreso Esperado Real (Stored)",
        currency_field="currency_id",
        compute="_compute_actual_metrics",
        store=True,
    )
    
    actual_revenue_display = fields.Char(
        string="Ingreso Esperado Real",
        compute="_compute_revenue_display",
        store=True,
    )
    
    # Porcentajes de cumplimiento (sin store - para vistas con widget percentage)
    leads_achievement = fields.Float(
        string="% Cumplimiento Leads",
        compute="_compute_achievement",
    )
    
    prospect_achievement = fields.Float(
        string="% Cumplimiento Prospectos",
        compute="_compute_achievement",
    )
    
    meeting_achievement = fields.Float(
        string="% Cumplimiento Citas",
        compute="_compute_achievement",
    )
    
    opportunity_achievement = fields.Float(
        string="% Cumplimiento Oportunidades",
        compute="_compute_achievement",
    )
    
    reserved_achievement = fields.Float(
        string="% Cumplimiento Apartados",
        compute="_compute_achievement",
    )
    
    closed_achievement = fields.Float(
        string="% Cumplimiento Cierres",
        compute="_compute_achievement",
    )
    
    # Porcentajes ESPEJO con store=True (0-1) - Compatibilidad
    leads_achievement_stored = fields.Float(
        string="% Cumplimiento Leads (Stored)",
        compute="_compute_achievement",
        store=True,
    )
    
    prospect_achievement_stored = fields.Float(
        string="% Cumplimiento Prospectos (Stored)",
        compute="_compute_achievement",
        store=True,
    )
    
    meeting_achievement_stored = fields.Float(
        string="% Cumplimiento Citas (Stored)",
        compute="_compute_achievement",
        store=True,
    )
    
    opportunity_achievement_stored = fields.Float(
        string="% Cumplimiento Oportunidades (Stored)",
        compute="_compute_achievement",
        store=True,
    )
    
    reserved_achievement_stored = fields.Float(
        string="% Cumplimiento Apartados (Stored)",
        compute="_compute_achievement",
        store=True,
    )
    
    closed_achievement_stored = fields.Float(
        string="% Cumplimiento Cierres (Stored)",
        compute="_compute_achievement",
        store=True,
    )
    
    # Porcentajes en escala 0-100 para Dashboard Ninja (Float con decimales)
    leads_achievement_pct = fields.Float(
        string="% Cumplimiento Leads (Dashboard)",
        compute="_compute_achievement",
        store=True,
        digits=(5, 2),  # Hasta 999.99%
    )
    
    prospect_achievement_pct = fields.Float(
        string="% Cumplimiento Prospectos (Dashboard)",
        compute="_compute_achievement",
        store=True,
        digits=(5, 2),
    )
    
    meeting_achievement_pct = fields.Float(
        string="% Cumplimiento Citas (Dashboard)",
        compute="_compute_achievement",
        store=True,
        digits=(5, 2),
    )
    
    opportunity_achievement_pct = fields.Float(
        string="% Cumplimiento Oportunidades (Dashboard)",
        compute="_compute_achievement",
        store=True,
        digits=(5, 2),
    )
    
    reserved_achievement_pct = fields.Float(
        string="% Cumplimiento Apartados (Dashboard)",
        compute="_compute_achievement",
        store=True,
        digits=(5, 2),
    )
    
    closed_achievement_pct = fields.Float(
        string="% Cumplimiento Cierres (Dashboard)",
        compute="_compute_achievement",
        store=True,
        digits=(5, 2),
    )
    
    # Campos Char para Dashboard Ninja (con símbolo %)
    leads_achievement_display = fields.Char(
        string="% Leads",
        compute="_compute_achievement_display",
        store=True,
    )
    
    prospect_achievement_display = fields.Char(
        string="% Prospectos",
        compute="_compute_achievement_display",
        store=True,
    )
    
    meeting_achievement_display = fields.Char(
        string="% Citas",
        compute="_compute_achievement_display",
        store=True,
    )
    
    opportunity_achievement_display = fields.Char(
        string="% Oportunidades",
        compute="_compute_achievement_display",
        store=True,
    )
    
    reserved_achievement_display = fields.Char(
        string="% Apartados",
        compute="_compute_achievement_display",
        store=True,
    )
    
    closed_achievement_display = fields.Char(
        string="% Cierres",
        compute="_compute_achievement_display",
        store=True,
    )
    
    @api.depends("start_date", "end_date", "goal_id.user_id", "goal_id.child_ids", "goal_id.child_ids.week_ids.actual_leads_stored")
    def _compute_actual_metrics(self):
        """Calcula las métricas reales desde el CRM o suma de metas hijas"""
        for record in self:
            # SI TIENE METAS HIJAS: Sumar valores de las semanas correspondientes
            if record.goal_id and record.goal_id.child_ids and record.start_date and record.end_date:
                leads_sum = 0
                prospect_sum = 0
                meeting_sum = 0
                opportunity_sum = 0
                reserved_sum = 0
                closed_sum = 0
                revenue_sum = 0
                
                for child_goal in record.goal_id.child_ids:
                    # Buscar la semana correspondiente en la meta hija
                    child_week = child_goal.week_ids.filtered(
                        lambda w: w.start_date == record.start_date and w.end_date == record.end_date
                    )
                    
                    if child_week:
                        leads_sum += child_week.actual_leads_stored
                        prospect_sum += child_week.actual_prospect_stored
                        meeting_sum += child_week.actual_meeting_stored
                        opportunity_sum += child_week.actual_opportunity_stored
                        reserved_sum += child_week.actual_reserved_stored
                        closed_sum += child_week.actual_closed_stored
                        revenue_sum += child_week.actual_revenue_stored
                
                # Asignar los valores sumados
                record.actual_leads = leads_sum
                record.actual_leads_stored = leads_sum
                record.actual_prospect = prospect_sum
                record.actual_prospect_stored = prospect_sum
                record.actual_meeting = meeting_sum
                record.actual_meeting_stored = meeting_sum
                record.actual_opportunity = opportunity_sum
                record.actual_opportunity_stored = opportunity_sum
                record.actual_reserved = reserved_sum
                record.actual_reserved_stored = reserved_sum
                record.actual_closed = closed_sum
                record.actual_closed_stored = closed_sum
                record.actual_revenue = revenue_sum
                record.actual_revenue_stored = revenue_sum
                continue
            
            # SI NO TIENE METAS HIJAS: Lógica original (buscar del CRM)
            if not record.start_date or not record.end_date or not record.goal_id.user_id:
                # Campos sin store (tiempo real)
                record.actual_leads = 0
                record.actual_prospect = 0
                record.actual_meeting = 0
                record.actual_opportunity = 0
                record.actual_reserved = 0
                record.actual_closed = 0
                record.actual_revenue = 0
                # Campos con store (para dashboard)
                record.actual_leads_stored = 0
                record.actual_prospect_stored = 0
                record.actual_meeting_stored = 0
                record.actual_opportunity_stored = 0
                record.actual_reserved_stored = 0
                record.actual_closed_stored = 0
                record.actual_revenue_stored = 0
                continue
            
            user_id = record.goal_id.user_id.id

            # Dominio base: leads creados en este período por este usuario
            base_domain = [
                ("create_date", ">=", record.start_date),
                ("create_date", "<=", record.end_date),
                ("user_id", "=", user_id),
            ]

            Lead = self.env["crm.lead"]

            # Conteo histórico: se cuenta si el lead PASÓ por la etapa (was_X = True)
            leads_count = Lead.search_count(base_domain + [("was_lead", "=", True)])
            record.actual_leads = leads_count
            record.actual_leads_stored = leads_count

            prospect_count = Lead.search_count(base_domain + [("was_prospect", "=", True)])
            record.actual_prospect = prospect_count
            record.actual_prospect_stored = prospect_count

            meeting_count = Lead.search_count(base_domain + [("was_meeting", "=", True)])
            record.actual_meeting = meeting_count
            record.actual_meeting_stored = meeting_count

            opportunity_count = Lead.search_count(base_domain + [("was_opportunity", "=", True)])
            record.actual_opportunity = opportunity_count
            record.actual_opportunity_stored = opportunity_count

            reserved_count = Lead.search_count(base_domain + [("was_reserved", "=", True)])
            record.actual_reserved = reserved_count
            record.actual_reserved_stored = reserved_count

            closed_count = Lead.search_count(base_domain + [("was_closed", "=", True)])
            record.actual_closed = closed_count
            record.actual_closed_stored = closed_count

            # Ingreso esperado real: suma de todos los leads del período
            all_leads = Lead.search(base_domain)
            total_revenue = sum(all_leads.mapped("expected_revenue"))
            record.actual_revenue = total_revenue
            record.actual_revenue_stored = total_revenue
    
    @api.depends("weekly_leads", "actual_leads_stored", "weekly_prospect", "actual_prospect_stored",
                 "weekly_meeting", "actual_meeting_stored", "weekly_opportunity", "actual_opportunity_stored",
                 "weekly_reserved", "actual_reserved_stored", "weekly_closed", "actual_closed_stored")
    def _compute_achievement(self):
        """Calcula porcentajes de cumplimiento"""
        for record in self:
            # Leads
            if record.weekly_leads > 0:
                pct = record.actual_leads_stored / record.weekly_leads
            else:
                pct = 0
            record.leads_achievement = pct
            record.leads_achievement_stored = pct
            record.leads_achievement_pct = pct * 100  # Para Dashboard (0-100)
            
            # Prospectos
            if record.weekly_prospect > 0:
                pct = record.actual_prospect_stored / record.weekly_prospect
            else:
                pct = 0
            record.prospect_achievement = pct
            record.prospect_achievement_stored = pct
            record.prospect_achievement_pct = pct * 100
            
            # Citas
            if record.weekly_meeting > 0:
                pct = record.actual_meeting_stored / record.weekly_meeting
            else:
                pct = 0
            record.meeting_achievement = pct
            record.meeting_achievement_stored = pct
            record.meeting_achievement_pct = pct * 100
            
            # Oportunidades
            if record.weekly_opportunity > 0:
                pct = record.actual_opportunity_stored / record.weekly_opportunity
            else:
                pct = 0
            record.opportunity_achievement = pct
            record.opportunity_achievement_stored = pct
            record.opportunity_achievement_pct = pct * 100
            
            # Apartados
            if record.weekly_reserved > 0:
                pct = record.actual_reserved_stored / record.weekly_reserved
            else:
                pct = 0
            record.reserved_achievement = pct
            record.reserved_achievement_stored = pct
            record.reserved_achievement_pct = pct * 100
            
            # Cierres
            if record.weekly_closed > 0:
                pct = record.actual_closed_stored / record.weekly_closed
            else:
                pct = 0
            record.closed_achievement = pct
            record.closed_achievement_stored = pct
            record.closed_achievement_pct = pct * 100
    
    @api.depends("leads_achievement_pct", "prospect_achievement_pct", "meeting_achievement_pct",
                 "opportunity_achievement_pct", "reserved_achievement_pct", "closed_achievement_pct")
    def _compute_achievement_display(self):
        """Calcula los campos de porcentaje con símbolo % para Dashboard Ninja"""
        for record in self:
            record.leads_achievement_display = f"{record.leads_achievement_pct:.2f}%"
            record.prospect_achievement_display = f"{record.prospect_achievement_pct:.2f}%"
            record.meeting_achievement_display = f"{record.meeting_achievement_pct:.2f}%"
            record.opportunity_achievement_display = f"{record.opportunity_achievement_pct:.2f}%"
            record.reserved_achievement_display = f"{record.reserved_achievement_pct:.2f}%"
            record.closed_achievement_display = f"{record.closed_achievement_pct:.2f}%"
    
    @api.depends("actual_revenue_stored", "currency_id")
    def _compute_revenue_display(self):
        """Formatea el ingreso real con separadores de miles y símbolo de moneda"""
        for record in self:
            if record.actual_revenue_stored:
                amount_str = "{:,.2f}".format(record.actual_revenue_stored)
                currency_symbol = record.currency_id.symbol or ""
                if record.currency_id.position == 'before':
                    record.actual_revenue_display = f"{currency_symbol}{amount_str}"
                else:
                    record.actual_revenue_display = f"{amount_str} {currency_symbol}"
            else:
                record.actual_revenue_display = "0.00"


class SaleGoalPeriodCRMIntegration(models.Model):
    _inherit = "sale.goal.period"
    
    # Campos CALCULADOS en tiempo real (sin store) - Para vistas normales
    actual_leads = fields.Integer(
        string="Leads Reales del Mes",
        compute="_compute_actual_from_weeks",
    )
    
    actual_prospect = fields.Integer(
        string="Prospectos Reales del Mes",
        compute="_compute_actual_from_weeks",
    )
    
    actual_meeting = fields.Integer(
        string="Citas Reales del Mes",
        compute="_compute_actual_from_weeks",
    )
    
    actual_opportunity = fields.Integer(
        string="Oportunidades Reales del Mes",
        compute="_compute_actual_from_weeks",
    )
    
    actual_reserved = fields.Integer(
        string="Apartados Reales del Mes",
        compute="_compute_actual_from_weeks",
    )
    
    actual_closed = fields.Integer(
        string="Cierres Reales del Mes",
        compute="_compute_actual_from_weeks",
    )
    
    actual_revenue = fields.Monetary(
        string="Ingreso Esperado Real del Mes",
        currency_field="currency_id",
        compute="_compute_actual_from_weeks",
    )
    
    # Campos ESPEJO con store=True - Para Dashboard Ninja (ocultos en vistas)
    actual_leads_stored = fields.Integer(
        string="Leads ingresados",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    
    actual_prospect_stored = fields.Integer(
        string="Prospectos ingresados",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    
    actual_meeting_stored = fields.Integer(
        string="Citas ingresadas",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    
    actual_opportunity_stored = fields.Integer(
        string="Oportunidades ingresadas",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    
    actual_reserved_stored = fields.Integer(
        string="Apartados ingresados",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    
    actual_closed_stored = fields.Integer(
        string="Cierres ingresados",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    
    actual_revenue_stored = fields.Monetary(
        string="Ingreso esperado del mes",
        currency_field="currency_id",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    
    actual_revenue_display = fields.Char(
        string="Ingreso esperado real",
        compute="_compute_revenue_display",
        store=True,
    )

    # Ingreso esperado real por etapa
    actual_revenue_lead = fields.Monetary(
        string="Ingreso Real Leads",
        currency_field="currency_id",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    actual_revenue_prospect = fields.Monetary(
        string="Ingreso Real Prospectos",
        currency_field="currency_id",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    actual_revenue_meeting = fields.Monetary(
        string="Ingreso Real Citas",
        currency_field="currency_id",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    actual_revenue_opportunity = fields.Monetary(
        string="Ingreso Real Oportunidades",
        currency_field="currency_id",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    actual_revenue_reserved = fields.Monetary(
        string="Ingreso Real Apartados",
        currency_field="currency_id",
        compute="_compute_actual_from_weeks",
        store=True,
    )
    actual_revenue_closed = fields.Monetary(
        string="Ingreso Real Cierres",
        currency_field="currency_id",
        compute="_compute_actual_from_weeks",
        store=True,
    )

    # Porcentaje de ingreso por etapa vs importe mensual
    lead_revenue_pct = fields.Float(
        string="% Ingreso Leads",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    prospect_revenue_pct = fields.Float(
        string="% Ingreso Prospectos",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    meeting_revenue_pct = fields.Float(
        string="% Ingreso Citas",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    opportunity_revenue_pct = fields.Float(
        string="% Ingreso Oportunidades",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    reserved_revenue_pct = fields.Float(
        string="% Ingreso Apartados",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    closed_revenue_pct = fields.Float(
        string="% Ingreso Cierres",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )

    # Campos Char de ingreso por etapa para Dashboard Ninja (formato monetario)
    lead_revenue_display = fields.Char(
        string="Ingreso Leads",
        compute="_compute_stage_revenue_display",
        store=True,
    )
    prospect_revenue_display = fields.Char(
        string="Ingreso Prospectos",
        compute="_compute_stage_revenue_display",
        store=True,
    )
    meeting_revenue_display = fields.Char(
        string="Ingreso Citas",
        compute="_compute_stage_revenue_display",
        store=True,
    )
    opportunity_revenue_display = fields.Char(
        string="Ingreso Oportunidades",
        compute="_compute_stage_revenue_display",
        store=True,
    )
    reserved_revenue_display = fields.Char(
        string="Ingreso Apartados",
        compute="_compute_stage_revenue_display",
        store=True,
    )
    closed_revenue_display = fields.Char(
        string="Ingreso Cierres",
        compute="_compute_stage_revenue_display",
        store=True,
    )

    # Campos Char de porcentaje por etapa para Dashboard Ninja (con símbolo %)
    lead_revenue_pct_display = fields.Char(
        string="% Ingreso Leads",
        compute="_compute_stage_revenue_display",
        store=True,
    )
    prospect_revenue_pct_display = fields.Char(
        string="% Ingreso Prospectos",
        compute="_compute_stage_revenue_display",
        store=True,
    )
    meeting_revenue_pct_display = fields.Char(
        string="% Ingreso Citas",
        compute="_compute_stage_revenue_display",
        store=True,
    )
    opportunity_revenue_pct_display = fields.Char(
        string="% Ingreso Oportunidades",
        compute="_compute_stage_revenue_display",
        store=True,
    )
    reserved_revenue_pct_display = fields.Char(
        string="% Ingreso Apartados",
        compute="_compute_stage_revenue_display",
        store=True,
    )
    closed_revenue_pct_display = fields.Char(
        string="% Ingreso Cierres",
        compute="_compute_stage_revenue_display",
        store=True,
    )

    monthly_amount_display = fields.Char(
        string="Importe mensual",
        compute="_compute_monthly_amount_display",
        store=True,
    )
    
    # Porcentajes de cumplimiento por etapa (sin store - para vistas)
    leads_achievement = fields.Float(
        string="% Cumplimiento Leads",
        compute="_compute_monthly_achievement",
    )
    
    prospect_achievement = fields.Float(
        string="% Cumplimiento Prospectos",
        compute="_compute_monthly_achievement",
    )
    
    meeting_achievement = fields.Float(
        string="% Cumplimiento Citas",
        compute="_compute_monthly_achievement",
    )
    
    opportunity_achievement = fields.Float(
        string="% Cumplimiento Oportunidades",
        compute="_compute_monthly_achievement",
    )
    
    reserved_achievement = fields.Float(
        string="% Cumplimiento Apartados",
        compute="_compute_monthly_achievement",
    )
    
    closed_achievement = fields.Float(
        string="% Cumplimiento Cierres",
        compute="_compute_monthly_achievement",
    )
    
    revenue_achievement = fields.Float(
        string="% Cumplimiento Ingresos",
        compute="_compute_monthly_achievement",
    )
    
    monthly_achievement = fields.Float(
        string="% Cumplimiento Mensual",
        compute="_compute_monthly_achievement",
    )
    
    # Porcentajes ESPEJO con store=True (0-1) - Compatibilidad
    leads_achievement_stored = fields.Float(
        string="% Cumplimiento Leads (Stored)",
        compute="_compute_monthly_achievement",
        store=True,
    )
    
    prospect_achievement_stored = fields.Float(
        string="% Cumplimiento Prospectos (Stored)",
        compute="_compute_monthly_achievement",
        store=True,
    )
    
    meeting_achievement_stored = fields.Float(
        string="% Cumplimiento Citas (Stored)",
        compute="_compute_monthly_achievement",
        store=True,
    )
    
    opportunity_achievement_stored = fields.Float(
        string="% Cumplimiento Oportunidades (Stored)",
        compute="_compute_monthly_achievement",
        store=True,
    )
    
    reserved_achievement_stored = fields.Float(
        string="% Cumplimiento Apartados (Stored)",
        compute="_compute_monthly_achievement",
        store=True,
    )
    
    closed_achievement_stored = fields.Float(
        string="% Cumplimiento Cierres (Stored)",
        compute="_compute_monthly_achievement",
        store=True,
    )
    
    revenue_achievement_stored = fields.Float(
        string="% Cumplimiento Ingresos (Stored)",
        compute="_compute_monthly_achievement",
        store=True,
    )
    
    monthly_achievement_stored = fields.Float(
        string="% Cumplimiento Mensual (Stored)",
        compute="_compute_monthly_achievement",
        store=True,
    )
    
    # Porcentajes en escala 0-100 para Dashboard Ninja (Float con decimales)
    leads_achievement_pct = fields.Float(
        string="% Cumplimiento Leads (Dashboard)",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    
    prospect_achievement_pct = fields.Float(
        string="% Cumplimiento Prospectos (Dashboard)",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    
    meeting_achievement_pct = fields.Float(
        string="% Cumplimiento Citas (Dashboard)",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    
    opportunity_achievement_pct = fields.Float(
        string="% Cumplimiento Oportunidades (Dashboard)",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    
    reserved_achievement_pct = fields.Float(
        string="% Cumplimiento Apartados (Dashboard)",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    
    closed_achievement_pct = fields.Float(
        string="% Cumplimiento Cierres (Dashboard)",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    
    revenue_achievement_pct = fields.Float(
        string="% Cumplimiento Ingresos (Dashboard)",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    
    monthly_achievement_pct = fields.Float(
        string="% Cumplimiento Mensual (Dashboard)",
        compute="_compute_monthly_achievement",
        store=True,
        digits=(5, 2),
    )
    
    # Campos Char para Dashboard Ninja (con símbolo %)
    leads_achievement_display = fields.Char(
        string="% Leads",
        compute="_compute_achievement_display",
        store=True,
    )
    
    prospect_achievement_display = fields.Char(
        string="% Prospectos",
        compute="_compute_achievement_display",
        store=True,
    )
    
    meeting_achievement_display = fields.Char(
        string="% Citas",
        compute="_compute_achievement_display",
        store=True,
    )
    
    opportunity_achievement_display = fields.Char(
        string="% Oportunidades",
        compute="_compute_achievement_display",
        store=True,
    )
    
    reserved_achievement_display = fields.Char(
        string="% Apartados",
        compute="_compute_achievement_display",
        store=True,
    )
    
    closed_achievement_display = fields.Char(
        string="% Cierres",
        compute="_compute_achievement_display",
        store=True,
    )
    
    revenue_achievement_display = fields.Char(
        string="% Ingresos",
        compute="_compute_achievement_display",
        store=True,
    )
    
    lead_ids = fields.Many2many(
        "crm.lead",
        "sale_goal_period_crm_lead_rel",
        "period_id",
        "lead_id",
        string="Leads del Período",
    )
    
    lead_count = fields.Integer(
        string="Cantidad de Leads",
        compute="_compute_lead_count",
        store=True,
    )
    
    @api.depends("week_ids.start_date", "week_ids.end_date", "goal_id.user_id", "goal_id.child_ids", "goal_id.child_ids.period_ids.actual_leads_stored")
    def _compute_actual_from_weeks(self):
        """Calcula las métricas reales del mes desde semanas o suma de metas hijas"""
        for record in self:
            # SI TIENE METAS HIJAS: Sumar valores de los períodos correspondientes
            if record.goal_id and record.goal_id.child_ids and record.period_number:
                leads_sum = 0
                prospect_sum = 0
                meeting_sum = 0
                opportunity_sum = 0
                reserved_sum = 0
                closed_sum = 0
                revenue_sum = 0
                revenue_lead_sum = 0
                revenue_prospect_sum = 0
                revenue_meeting_sum = 0
                revenue_opportunity_sum = 0
                revenue_reserved_sum = 0
                revenue_closed_sum = 0
                
                for child_goal in record.goal_id.child_ids:
                    # Buscar el período correspondiente en la meta hija
                    child_period = child_goal.period_ids.filtered(
                        lambda p: p.period_number == record.period_number
                    )
                    
                    if child_period:
                        leads_sum += child_period.actual_leads_stored
                        prospect_sum += child_period.actual_prospect_stored
                        meeting_sum += child_period.actual_meeting_stored
                        opportunity_sum += child_period.actual_opportunity_stored
                        reserved_sum += child_period.actual_reserved_stored
                        closed_sum += child_period.actual_closed_stored
                        revenue_sum += child_period.actual_revenue_stored
                        revenue_lead_sum += child_period.actual_revenue_lead
                        revenue_prospect_sum += child_period.actual_revenue_prospect
                        revenue_meeting_sum += child_period.actual_revenue_meeting
                        revenue_opportunity_sum += child_period.actual_revenue_opportunity
                        revenue_reserved_sum += child_period.actual_revenue_reserved
                        revenue_closed_sum += child_period.actual_revenue_closed
                
                # Asignar los valores sumados
                record.actual_leads = leads_sum
                record.actual_leads_stored = leads_sum
                record.actual_prospect = prospect_sum
                record.actual_prospect_stored = prospect_sum
                record.actual_meeting = meeting_sum
                record.actual_meeting_stored = meeting_sum
                record.actual_opportunity = opportunity_sum
                record.actual_opportunity_stored = opportunity_sum
                record.actual_reserved = reserved_sum
                record.actual_reserved_stored = reserved_sum
                record.actual_closed = closed_sum
                record.actual_closed_stored = closed_sum
                record.actual_revenue = revenue_sum
                record.actual_revenue_stored = revenue_sum
                record.actual_revenue_lead = revenue_lead_sum
                record.actual_revenue_prospect = revenue_prospect_sum
                record.actual_revenue_meeting = revenue_meeting_sum
                record.actual_revenue_opportunity = revenue_opportunity_sum
                record.actual_revenue_reserved = revenue_reserved_sum
                record.actual_revenue_closed = revenue_closed_sum
                continue
            
            # SI NO TIENE METAS HIJAS: Lógica original (desde semanas propias)
            if not record.week_ids or not record.goal_id.user_id:
                record.actual_leads = 0
                record.actual_leads_stored = 0
                record.actual_prospect = 0
                record.actual_prospect_stored = 0
                record.actual_meeting = 0
                record.actual_meeting_stored = 0
                record.actual_opportunity = 0
                record.actual_opportunity_stored = 0
                record.actual_reserved = 0
                record.actual_reserved_stored = 0
                record.actual_closed = 0
                record.actual_closed_stored = 0
                record.actual_revenue = 0
                record.actual_revenue_stored = 0
                record.actual_revenue_lead = 0
                record.actual_revenue_prospect = 0
                record.actual_revenue_meeting = 0
                record.actual_revenue_opportunity = 0
                record.actual_revenue_reserved = 0
                record.actual_revenue_closed = 0
                continue

            start_date = min(record.week_ids.mapped("start_date"))
            end_date = max(record.week_ids.mapped("end_date"))
            user_id = record.goal_id.user_id.id

            Lead = self.env["crm.lead"]

            base_domain = [
                ("create_date", ">=", start_date),
                ("create_date", "<=", end_date),
                ("user_id", "=", user_id),
            ]

            # Conteo histórico: se cuenta si el lead PASÓ por la etapa (was_X = True)
            leads = Lead.search_count(base_domain + [("was_lead", "=", True)])
            record.actual_leads = leads
            record.actual_leads_stored = leads

            prospect = Lead.search_count(base_domain + [("was_prospect", "=", True)])
            record.actual_prospect = prospect
            record.actual_prospect_stored = prospect

            meeting = Lead.search_count(base_domain + [("was_meeting", "=", True)])
            record.actual_meeting = meeting
            record.actual_meeting_stored = meeting

            opportunity = Lead.search_count(base_domain + [("was_opportunity", "=", True)])
            record.actual_opportunity = opportunity
            record.actual_opportunity_stored = opportunity

            reserved = Lead.search_count(base_domain + [("was_reserved", "=", True)])
            record.actual_reserved = reserved
            record.actual_reserved_stored = reserved

            closed = Lead.search_count(base_domain + [("was_closed", "=", True)])
            record.actual_closed = closed
            record.actual_closed_stored = closed

            # Ingreso esperado real: suma de todos los leads del período
            all_leads = Lead.search(base_domain)
            revenue = sum(all_leads.mapped("expected_revenue"))
            record.actual_revenue = revenue
            record.actual_revenue_stored = revenue

            # Ingreso esperado real por etapa (histórico)
            leads_lead = Lead.search(base_domain + [("was_lead", "=", True)])
            record.actual_revenue_lead = sum(leads_lead.mapped("expected_revenue"))

            leads_prospect = Lead.search(base_domain + [("was_prospect", "=", True)])
            record.actual_revenue_prospect = sum(leads_prospect.mapped("expected_revenue"))

            leads_meeting = Lead.search(base_domain + [("was_meeting", "=", True)])
            record.actual_revenue_meeting = sum(leads_meeting.mapped("expected_revenue"))

            leads_opportunity = Lead.search(base_domain + [("was_opportunity", "=", True)])
            record.actual_revenue_opportunity = sum(leads_opportunity.mapped("expected_revenue"))

            leads_reserved = Lead.search(base_domain + [("was_reserved", "=", True)])
            record.actual_revenue_reserved = sum(leads_reserved.mapped("expected_revenue"))

            leads_closed = Lead.search(base_domain + [("was_closed", "=", True)])
            record.actual_revenue_closed = sum(leads_closed.mapped("expected_revenue"))
    
    @api.depends("monthly_leads", "actual_leads_stored", "monthly_prospect", "actual_prospect_stored",
                 "monthly_meeting", "actual_meeting_stored", "monthly_opportunity", "actual_opportunity_stored",
                 "monthly_reserved", "actual_reserved_stored", "monthly_closed", "actual_closed_stored",
                 "monthly_amount", "actual_revenue_stored",
                 "actual_revenue_lead", "actual_revenue_prospect", "actual_revenue_meeting",
                 "actual_revenue_opportunity", "actual_revenue_reserved", "actual_revenue_closed")
    def _compute_monthly_achievement(self):
        """Calcula el porcentaje de cumplimiento para cada etapa del mes"""
        for record in self:
            # Leads
            if record.monthly_leads > 0:
                pct = record.actual_leads_stored / record.monthly_leads
            else:
                pct = 0
            record.leads_achievement = pct
            record.leads_achievement_stored = pct
            record.leads_achievement_pct = pct * 100
            
            # Prospectos
            if record.monthly_prospect > 0:
                pct = record.actual_prospect_stored / record.monthly_prospect
            else:
                pct = 0
            record.prospect_achievement = pct
            record.prospect_achievement_stored = pct
            record.prospect_achievement_pct = pct * 100
            
            # Citas
            if record.monthly_meeting > 0:
                pct = record.actual_meeting_stored / record.monthly_meeting
            else:
                pct = 0
            record.meeting_achievement = pct
            record.meeting_achievement_stored = pct
            record.meeting_achievement_pct = pct * 100
            
            # Oportunidades
            if record.monthly_opportunity > 0:
                pct = record.actual_opportunity_stored / record.monthly_opportunity
            else:
                pct = 0
            record.opportunity_achievement = pct
            record.opportunity_achievement_stored = pct
            record.opportunity_achievement_pct = pct * 100
            
            # Apartados
            if record.monthly_reserved > 0:
                pct = record.actual_reserved_stored / record.monthly_reserved
            else:
                pct = 0
            record.reserved_achievement = pct
            record.reserved_achievement_stored = pct
            record.reserved_achievement_pct = pct * 100
            
            # Cierres
            if record.monthly_closed > 0:
                pct = record.actual_closed_stored / record.monthly_closed
            else:
                pct = 0
            record.closed_achievement = pct
            record.closed_achievement_stored = pct
            record.closed_achievement_pct = pct * 100
            
            # Ingresos (comparar con meta mensual)
            if record.monthly_amount > 0:
                pct = record.actual_revenue_stored / record.monthly_amount
            else:
                pct = 0
            record.revenue_achievement = pct
            record.revenue_achievement_stored = pct
            record.revenue_achievement_pct = pct * 100
            
            # Cumplimiento mensual (basado en cierres)
            record.monthly_achievement = record.closed_achievement
            record.monthly_achievement_stored = record.closed_achievement_stored
            record.monthly_achievement_pct = record.closed_achievement_pct

            # Porcentaje de ingreso esperado por etapa vs importe mensual
            monthly = record.monthly_amount or 0
            record.lead_revenue_pct = (record.actual_revenue_lead / monthly * 100) if monthly else 0
            record.prospect_revenue_pct = (record.actual_revenue_prospect / monthly * 100) if monthly else 0
            record.meeting_revenue_pct = (record.actual_revenue_meeting / monthly * 100) if monthly else 0
            record.opportunity_revenue_pct = (record.actual_revenue_opportunity / monthly * 100) if monthly else 0
            record.reserved_revenue_pct = (record.actual_revenue_reserved / monthly * 100) if monthly else 0
            record.closed_revenue_pct = (record.actual_revenue_closed / monthly * 100) if monthly else 0
    
    @api.depends("leads_achievement_pct", "prospect_achievement_pct", "meeting_achievement_pct",
                 "opportunity_achievement_pct", "reserved_achievement_pct", "closed_achievement_pct",
                 "revenue_achievement_pct")
    def _compute_achievement_display(self):
        """Calcula los campos de porcentaje con símbolo % para Dashboard Ninja"""
        for record in self:
            record.leads_achievement_display = f"{record.leads_achievement_pct:.2f}%"
            record.prospect_achievement_display = f"{record.prospect_achievement_pct:.2f}%"
            record.meeting_achievement_display = f"{record.meeting_achievement_pct:.2f}%"
            record.opportunity_achievement_display = f"{record.opportunity_achievement_pct:.2f}%"
            record.reserved_achievement_display = f"{record.reserved_achievement_pct:.2f}%"
            record.closed_achievement_display = f"{record.closed_achievement_pct:.2f}%"
            record.revenue_achievement_display = f"{record.revenue_achievement_pct:.2f}%"
    
    @api.depends("actual_revenue_stored", "currency_id")
    def _compute_revenue_display(self):
        """Formatea el ingreso real con separadores de miles y símbolo de moneda"""
        for record in self:
            if record.actual_revenue_stored:
                amount_str = "{:,.2f}".format(record.actual_revenue_stored)
                currency_symbol = record.currency_id.symbol or ""
                if record.currency_id.position == 'before':
                    record.actual_revenue_display = f"{currency_symbol}{amount_str}"
                else:
                    record.actual_revenue_display = f"{amount_str} {currency_symbol}"
            else:
                record.actual_revenue_display = "0.00"
    
    @api.depends("actual_revenue_lead", "actual_revenue_prospect", "actual_revenue_meeting",
                 "actual_revenue_opportunity", "actual_revenue_reserved", "actual_revenue_closed",
                 "lead_revenue_pct", "prospect_revenue_pct", "meeting_revenue_pct",
                 "opportunity_revenue_pct", "reserved_revenue_pct", "closed_revenue_pct",
                 "currency_id")
    def _compute_stage_revenue_display(self):
        """Formatea ingresos y porcentajes por etapa para Dashboard Ninja"""
        for record in self:
            symbol = record.currency_id.symbol or ""
            before = record.currency_id.position == "before"

            def fmt_money(val):
                amount = "{:,.2f}".format(val)
                return f"{symbol}{amount}" if before else f"{amount} {symbol}"

            record.lead_revenue_display = fmt_money(record.actual_revenue_lead)
            record.prospect_revenue_display = fmt_money(record.actual_revenue_prospect)
            record.meeting_revenue_display = fmt_money(record.actual_revenue_meeting)
            record.opportunity_revenue_display = fmt_money(record.actual_revenue_opportunity)
            record.reserved_revenue_display = fmt_money(record.actual_revenue_reserved)
            record.closed_revenue_display = fmt_money(record.actual_revenue_closed)

            record.lead_revenue_pct_display = f"{record.lead_revenue_pct:.2f}%"
            record.prospect_revenue_pct_display = f"{record.prospect_revenue_pct:.2f}%"
            record.meeting_revenue_pct_display = f"{record.meeting_revenue_pct:.2f}%"
            record.opportunity_revenue_pct_display = f"{record.opportunity_revenue_pct:.2f}%"
            record.reserved_revenue_pct_display = f"{record.reserved_revenue_pct:.2f}%"
            record.closed_revenue_pct_display = f"{record.closed_revenue_pct:.2f}%"

    @api.depends("monthly_amount", "currency_id")
    def _compute_monthly_amount_display(self):
        """Formatea el importe mensual con separadores de miles y símbolo de moneda"""
        for record in self:
            if record.monthly_amount:
                amount_str = "{:,.2f}".format(record.monthly_amount)
                currency_symbol = record.currency_id.symbol or ""
                if record.currency_id.position == 'before':
                    record.monthly_amount_display = f"{currency_symbol}{amount_str}"
                else:
                    record.monthly_amount_display = f"{amount_str} {currency_symbol}"
            else:
                record.monthly_amount_display = "0.00"
    
    @api.depends("lead_ids")
    def _compute_lead_count(self):
        for record in self:
            record.lead_count = len(record.lead_ids)
    
    def update_period_leads(self):
        """Actualiza los leads del período desde el CRM"""
        self.ensure_one()
        
        if not self.week_ids or not self.goal_id.user_id:
            self.lead_ids = False
            return
        
        weeks = self.week_ids
        start_date = min(weeks.mapped("start_date"))
        end_date = max(weeks.mapped("end_date"))
        user_id = self.goal_id.user_id.id
        
        leads = self.env["crm.lead"].search([
            ("create_date", ">=", start_date),
            ("create_date", "<=", end_date),
            ("user_id", "=", user_id),
        ])
        
        self.lead_ids = leads
    
    def action_view_leads(self):
        self.ensure_one()
        # Actualizar leads antes de mostrar
        self.update_period_leads()
        
        return {
            "type": "ir.actions.act_window",
            "name": f"Leads de {self.period_name}",
            "res_model": "crm.lead",
            "view_mode": "list,form",
            "domain": [("id", "in", self.lead_ids.ids)],
            "context": {"create": False},
        }
    
    def action_force_recompute(self):
        """Fuerza el recálculo de todos los porcentajes"""
        self.ensure_one()
        
        # Forzar recálculo de semanas
        for week in self.week_ids:
            week._compute_actual_metrics()
        
        # Forzar recálculo de métricas del mes
        self._compute_actual_from_weeks()
        
        # Forzar recálculo de porcentajes
        self._compute_monthly_achievement()
        
        # Invalidar cache y forzar guardado
        self.invalidate_recordset()
        self.flush_recordset()
        
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "✅ Recalculado",
                "message": f"Porcentajes actualizados correctamente",
                "type": "success",
                "sticky": False,
            },
        }


class CrmLeadPeriodRelation(models.Model):
    _inherit = "crm.lead"
    
    period_ids = fields.Many2many(
        "sale.goal.period",
        "sale_goal_period_crm_lead_rel",
        "lead_id",
        "period_id",
        string="Períodos",
    )
    
    # Campos que registran si pasó por cada etapa
    was_lead = fields.Boolean(
        string="Pasó por Lead",
        default=False,
        copy=False,
    )
    
    was_prospect = fields.Boolean(
        string="Pasó por Prospecto",
        default=False,
        copy=False,
    )
    
    was_meeting = fields.Boolean(
        string="Tuvo Cita",
        default=False,
        copy=False,
    )
    
    was_opportunity = fields.Boolean(
        string="Pasó por Oportunidad",
        default=False,
        copy=False,
    )
    
    was_reserved = fields.Boolean(
        string="Pasó por Apartado",
        default=False,
        copy=False,
    )
    
    was_closed = fields.Boolean(
        string="Pasó por Cierre",
        default=False,
        copy=False,
    )
    
    # Fechas en que pasó por cada etapa
    lead_date = fields.Datetime(
        string="Fecha Lead",
        readonly=True,
        copy=False,
    )
    
    prospect_date = fields.Datetime(
        string="Fecha Prospecto",
        readonly=True,
        copy=False,
    )
    
    meeting_date = fields.Datetime(
        string="Fecha Cita",
        readonly=True,
        copy=False,
    )
    
    opportunity_date = fields.Datetime(
        string="Fecha Oportunidad",
        readonly=True,
        copy=False,
    )
    
    reserved_date = fields.Datetime(
        string="Fecha Apartado",
        readonly=True,
        copy=False,
    )
    
    closed_date = fields.Datetime(
        string="Fecha Cierre",
        readonly=True,
        copy=False,
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        """Marcar la etapa inicial al crear"""
        records = super().create(vals_list)
        for record in records:
            record._update_stage_tracking()
        records._trigger_goal_recompute()
        return records
    
    def write(self, vals):
        """Detectar cambios de etapa y marcar"""
        result = super().write(vals)
        if "stage_id" in vals:
            self._update_stage_tracking()
            self._trigger_goal_recompute()
        return result
    
    def _trigger_goal_recompute(self):
        """Recalcula automaticamente las semanas y periodos afectados cuando cambia la etapa de un lead"""
        weeks_to_recompute = self.env["sale.goal.week"]
        
        for record in self:
            if not record.user_id or not record.create_date:
                continue
            
            create_date = record.create_date.date()
            
            weeks = self.env["sale.goal.week"].search([
                ("goal_id.user_id", "=", record.user_id.id),
                ("start_date", "<=", create_date),
                ("end_date", ">=", create_date),
            ])
            weeks_to_recompute |= weeks
        
        if weeks_to_recompute:
            weeks_to_recompute._compute_actual_metrics()
            periods = weeks_to_recompute.mapped("period_id")
            if periods:
                periods._compute_actual_from_weeks()
                periods._compute_monthly_achievement()
    
    def _update_stage_tracking(self):
        """Actualiza los campos de seguimiento según la etapa actual"""
        for record in self:
            if not record.stage_id:
                continue
            
            stage_name = record.stage_id.name.lower()
            
            # Lead
            if "lead" in stage_name and not record.was_lead:
                record.was_lead = True
                record.lead_date = fields.Datetime.now()
            
            # Prospecto
            if "prospect" in stage_name or "prospecto" in stage_name:
                if not record.was_prospect:
                    record.was_prospect = True
                    record.prospect_date = fields.Datetime.now()
            
            # Cita/Meeting
            if "cita" in stage_name or "meeting" in stage_name or "reunión" in stage_name or "reunion" in stage_name:
                if not record.was_meeting:
                    record.was_meeting = True
                    record.meeting_date = fields.Datetime.now()
            
            # Oportunidad
            if "oportunidad" in stage_name or "opportunity" in stage_name:
                if not record.was_opportunity:
                    record.was_opportunity = True
                    record.opportunity_date = fields.Datetime.now()
            
            # Apartado
            if "apartado" in stage_name or "reserv" in stage_name:
                if not record.was_reserved:
                    record.was_reserved = True
                    record.reserved_date = fields.Datetime.now()
            
            # Cierre/Ganado - requiere physical_delivery_date en propiedad Y cuota 0 pagada
            if record.stage_id.is_won and not record.was_closed:
                property_has_delivery_date = bool(
                    record.property_id and record.property_id.physical_delivery_date
                )
                cuota_0_paid = False
                if record.property_id:
                    contract = self.env["property.contract"].search([
                        ("property_id", "=", record.property_id.id),
                        ("state", "=", "confirmed"),
                    ], limit=1)
                    if contract:
                        loan_line_0 = self.env["loan.line"].search([
                            ("contract_id", "=", contract.id),
                            ("count_line", "=", 0),
                            ("payment_state", "=", "paid"),
                        ], limit=1)
                        cuota_0_paid = bool(loan_line_0)
                if property_has_delivery_date and cuota_0_paid:
                    record.was_closed = True
                    record.closed_date = fields.Datetime.now()            
            # Cancelado - resetear apartado y cierre
            if "cancelado" in stage_name or "cancel" in stage_name:
                record.was_reserved = False
                record.was_closed = False