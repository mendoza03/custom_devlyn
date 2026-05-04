# -*- coding: utf-8 -*-
{
    "name": "CCIMA Dashboards",
    'version': '18.0.1.0.0',
    "category": "Sales/CRM",
    "summary": "Custom Dashboards for Advisor, Manager and Management",
    "description": """
        Module that provides three custom dashboards:
        - Advisor Dashboard
        - Manager Dashboard
        - Management Dashboard
    """,
    "author": "Axeel",
    "website": "https://www.ccima.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "crm",
        "ks_dashboard_ninja"           
    ],
    "data": [
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}