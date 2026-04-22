{
    "name": "Helpdesk Sections",
    "version": "19.0.1.0.0",
    "category": "Helpdesk",
    "summary": "Sections catalog for Helpdesk configuration",
    "depends": ["helpdesk","web"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/helpdesk_section_views.xml",
        "views/helpdesk_ticket_form_replace.xml",
        "views/helpdesk_ticket_attachments_views.xml",
        "views/helpdesk_category_views.xml",
        "views/helpdesk_subcategory_views.xml",
        "views/helpdesk_section_menu.xml",
        "views/helpdesk_ticket_form_facturacion.xml",
        "data/helpdesk_section_data.xml",
        "data/helpdesk_category_data.xml",
        "data/helpdesk_subcategory_data.xml",

    ],
    
    "assets": {
        "web.assets_backend": [
            "helpdesk_custom_datos/static/src/js/auto_open_facturacion_modal.js",
        ],
    },

    "installable": True,
    "application": False,
    "license": "LGPL-3",
}