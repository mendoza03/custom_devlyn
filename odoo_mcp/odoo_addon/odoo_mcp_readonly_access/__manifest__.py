{
    "name": "Odoo MCP Readonly Access",
    "version": "19.0.1.0.0",
    "summary": "Readonly security layer for Devlyn MCP integration",
    "author": "BSP",
    "depends": [
        "base",
        "hr_attendance",
        "project",
        "helpdesk",
        "hr_biometric_attendance_sync",
        "devlyn_dahua_attendance_reporting",
    ],
    "data": [
        "security/odoo_mcp_groups.xml",
        "security/odoo_mcp_rules.xml",
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
