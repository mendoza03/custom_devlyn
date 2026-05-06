{
    "name": "Devlyn Dahua Asistencias por Sucursal",
    "version": "19.0.1.0.0",
    "summary": "Catalogos vivos y reporte XLSX de asistencias por sucursal",
    "author": "BSP",
    "depends": ["hr_attendance", "hr_biometric_attendance_sync"],
    "data": [
        "security/ir.model.access.csv",
        "views/devlyn_catalog_views.xml",
        "views/devlyn_catalog_reload_wizard_views.xml",
        "views/devlyn_attendance_branch_report_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "external_dependencies": {"python": ["xlsxwriter"]},
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
