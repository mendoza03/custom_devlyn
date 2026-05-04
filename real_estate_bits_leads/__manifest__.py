# -*- coding: utf-8 -*-

{
    "name": "Real Estate - Leads",
    "description": """
=====================================
Real Estate - Leads
=====================================
Add lead assignment
    """,
    "version": "18.0.0.0.1",
    "category": "Hidden",
    "license": "OPL-1",
    "depends": [
        "crm",
        "real_estate_bits",
    ],
    "data": [
        "data/ir_cron_data.xml",
        "security/ir.model.access.csv",
        "views/crm_team_views.xml",
        "views/utm_campaign_views.xml",
    ],
    "support": "luisangel-glez",
    "auto_install": False,
    "installable": True,
}