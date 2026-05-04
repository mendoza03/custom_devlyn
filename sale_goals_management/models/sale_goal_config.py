# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleGoalConfig(models.Model):
    _name = "sale.goal.config"
    _description = "Configuración de Metas de Ventas"
    
    name = fields.Char(
        string="Nombre",
        default="Configuración de Metas",
        required=True,
    )
    
    average_unit_price = fields.Monetary(
        string="Precio Promedio por Unidad",
        currency_field="currency_id",
        default=4500000,
        required=True,
        help="Precio promedio de una unidad inmobiliaria",
    )
    
    leads_per_unit = fields.Integer(
        string="Leads por Unidad",
        default=48,
        required=True,
        help="Número de leads necesarios para vender una unidad",
    )
    
    prospect_rate = fields.Float(
        string="% Conversión a Prospecto",
        default=50.0,
        required=True,
        help="Porcentaje de leads que se convierten en prospectos",
    )
    
    meeting_rate = fields.Float(
        string="% Conversión a Cita",
        default=50.0,
        required=True,
        help="Porcentaje de prospectos que se convierten en citas",
    )
    
    opportunity_rate = fields.Float(
        string="% Conversión a Oportunidad",
        default=33.33,
        required=True,
        help="Porcentaje de citas que se convierten en oportunidades",
    )
    
    reserved_rate = fields.Float(
        string="% Conversión a Apartado",
        default=25.0,
        required=True,
        help="Porcentaje de oportunidades que se apartan",
    )
    
    closed_rate = fields.Float(
        string="% Conversión a Cierre",
        default=100.0,
        required=True,
        help="Porcentaje de apartados que se cierran",
    )
    
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    
    calendar_ids = fields.One2many(
        "sale.goal.calendar",
        "config_id",
        string="Calendarios Anuales",
    )
    
    calendar_count = fields.Integer(
        string="Cantidad de Calendarios",
        compute="_compute_calendar_count",
    )
    
    @api.depends("calendar_ids")
    def _compute_calendar_count(self):
        for record in self:
            record.calendar_count = len(record.calendar_ids)
    
    @api.constrains("name")
    def _check_singleton(self):
        """Asegurar que solo exista un registro de configuración"""
        if self.search_count([]) > 1:
            raise ValidationError(
                "Solo puede existir una configuración de metas. "
                "Por favor, edite la configuración existente en lugar de crear una nueva."
            )
    
    @api.model
    def get_config(self):
        """Obtener o crear la configuración única"""
        config = self.search([], limit=1)
        if not config:
            config = self.create({
                "name": "Configuración de Metas",
            })
        return config
    
    def action_create_calendar(self):
        self.ensure_one()
        
        current_year = str(fields.Date.today().year)
        
        return {
            "type": "ir.actions.act_window",
            "name": "Crear Calendario Anual",
            "res_model": "sale.goal.calendar",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_config_id": self.id,
                "default_year": current_year,
                "force_save": True,
            },
        }
    
    def action_view_calendars(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Calendarios Anuales",
            "res_model": "sale.goal.calendar",
            "view_mode": "tree,form",
            "domain": [("config_id", "=", self.id)],
            "context": {
                "default_config_id": self.id,
            },
        }