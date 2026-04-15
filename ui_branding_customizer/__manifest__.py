{
    "name": "UI Branding Customizer",
    "version": "19.0.1.0.0",
    "summary": "Dynamic backend branding customizer",
    "description": """
        Generic module to customize backend colors, fonts, buttons, menus,
        navbar and UI preview dynamically.
    """,
    "category": "Tools",
    "author": "Carlos Andres Estrada",
    "license": "LGPL-3",
    "depends": [
        "base",
        "base_setup",
        "web",
        "jazzy_backend_theme",
    ],
    "data": [
        "views/res_config_settings_views.xml",
        "security/ir.model.access.csv",
    ],
    "assets": {
        "web.assets_backend": [
            "ui_branding_customizer/static/src/scss/backend_theme.scss",
            "ui_branding_customizer/static/src/js/theme_customizer.js",
        ],
    },
    "installable": True,
    "application": False,
}