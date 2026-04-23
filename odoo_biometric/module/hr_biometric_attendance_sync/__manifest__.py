{
    "name": "HR Biometric Attendance Sync",
    "version": "19.0.1.0.0",
    "summary": "Provisional biometric attendance sync from biometric_ingest to hr_attendance",
    "author": "BSP",
    "depends": ["hr_attendance"],
    "data": [
        "security/ir.model.access.csv",
        "data/hr_biometric_sync_data.xml",
        "views/hr_biometric_event_views.xml",
        "views/hr_biometric_sync_run_views.xml",
        "views/hr_biometric_sync_config_views.xml",
        "views/hr_biometric_menu.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
