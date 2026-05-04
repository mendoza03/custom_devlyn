{
    "name": "Helpdesk SLA Enterprise XLSX Reports",
    "version": "19.0.1.0.0",
    "category": "Helpdesk/Reporting",
    "summary": "Enterprise XLSX SLA reports for Helpdesk tickets.",
    "description": """
Enterprise XLSX SLA reporting for Helpdesk.

Features:
- Enterprise XLSX export without SQL views.
- Security groups for users and managers.
- Wizard with period, teams, agents, and report options.
- Closed ticket analysis.
- SLA compliance metrics.
- First response time calculation.
- Resolution time calculation.
- Executive summary sheet.
- SLA details sheet.
- Team summary sheet.
- Agent summary sheet.
- Monthly summary sheet.
    """,
    "author": "Custom Dev",
    "license": "LGPL-3",
    "depends": [
        "helpdesk",
        "mail"
    ],
    "data": [
        "security/helpdesk_sla_security.xml",
        "security/ir.model.access.csv",
        "views/helpdesk_sla_wizard_views.xml",
        "views/helpdesk_sla_menus.xml",
    ],
    "application": False,
    "installable": True,
}
