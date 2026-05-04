# -*- coding: utf-8 -*-
{
    "name": "Gestión de Metas de Ventas",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Gestión de metas de ventas con embudo de conversión",
    "description": """
        Gestión de Metas de Ventas
        ===========================
        * Define metas anuales por importe y convierte a objetivos de leads
        * Embudo de conversión: Leads → Prospecto → Cita → Oportunidad → Apartado → Cierre
        * Estructura jerárquica: CCO → DVN → Gerente → Asesor
        * Metas por período: Anual, Mensual, Semanal, Diario
        * Todos los cálculos con redondeo hacia arriba
    """,
    "author": "Axeel",
    "website": "https://www.ccima.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "sale_management",
        "crm",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sale_goals_data.xml",
        "views/sale_goal_config_views.xml",
        "views/sale_goal_views.xml",
        "views/sale_goals_menu.xml",
        "views/crm.xml",
        "views/sale_goal_crm_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
