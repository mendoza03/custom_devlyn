{
    "name": "Helpdesk Sections",
    "version": "19.0.1.0.0",
    "category": "Helpdesk",
    "summary": "Sections catalog for Helpdesk configuration",
    "depends": ["helpdesk"],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_section_views.xml",
        "views/helpdesk_ticket_form_replace.xml",
        "views/helpdesk_ticket_attachments_views.xml",
        "views/helpdesk_category_views.xml",
        "views/helpdesk_subcategory_views.xml",
        "views/helpdesk_section_menu.xml",
        "data/helpdesk_section_data.xml",
        "data/helpdesk_category_data.xml",
        "data/helpdesk_subcategory_data.xml",

    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}