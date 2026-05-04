{
    "name": "Real estate | Property management | Sale and Rental Contract management",
    "version": '18.0.5.0.0',
    'category': 'Services',
    "sequence": 14,
    "summary": """
        This module allows you to manage the real estate project, sell and rental property contracts, and calculate broker commission and many more.
        Advanced Property Sale & Rental Management | Property Sales | Property Rental 
    """,
    "description": """ 
        This module allows you to manage the real estate project, sell and rental property contracts, and calculate broker commission and many more.
        Advanced Property Sale & Rental Management | Property Sales | Property Rental 
    """,
    "author": "Terabits Technolab",
    "website": "https://www.terabits.xyz",
    "depends": ["base", "account", "crm", "analytic", 'repair', 'sale_management', 'web'],
    "license": "OPL-1",
    "price": "399.99",
    "currency": "USD",
    "data": [
        "data/ir_sequence.xml",
        "data/ir_action_server.xml",
        "data/email_template.xml",
        "data/real_estate_data.xml",
        'security/ir.model.access.csv',
        "views/view_account_invoice.xml",
        "views/view_attachment_line.xml",
        "views/view_crm_lead.xml",
        "views/view_crm_team.xml",
        "views/view_installment_template.xml",
        "views/view_product_category.xml",
        "views/view_project_worksite.xml",
        "views/view_property.xml",
        "views/view_condominium.xml",
        "views/view_property_contract.xml",
        "views/view_property_reservation.xml",
        "views/view_region.xml",
        "views/view_repair_order.xml",
        "views/view_res_config_settings.xml",
        "views/view_sale_order.xml",
        "views/view_sales_commission.xml",
        "views/menu_items.xml",
        "reports/contract_sale_report_templates.xml",
        "reports/report_statemet.xml",
    ],
    "assets": {
        "web.assets_backend": [
            #"real_estate_bits/static/src/libs/Chart.min.js",
            "real_estate_bits/static/src/xml/gmap.xml",
            # "real_estate_bits/static/src/js/init.js",
            # "real_estate_bits/static/src/js/map_widget.js",
            # "real_estate_bits/static/src/js/map_widget_multi.js",
            "real_estate_bits/static/src/js/place_autocomplete.js",
            # "real_estate_bits/static/src/js/place_autocomplete_multi.js",
            "real_estate_bits/static/src/xml/dashboard_view.xml",
            "real_estate_bits/static/src/xml/autocomplete.xml",
            "real_estate_bits/static/src/css/dashboard_view.css",
            "real_estate_bits/static/src/js/dashboard_view.js",
        ],
    },
    'external_dependencies': {
        "python": [
            "numerize",
        ],
    },
    "images": ["static/description/banner.gif"],
    'live_test_url': 'https://www.terabits.xyz/request_demo?source=index&version=16&app=real_estate_bits',
    "installable": True,
    "auto_install": False,
    "application": True,

}
