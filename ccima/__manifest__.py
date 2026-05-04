# -*- coding: utf-8 -*-

{
    "name": "CCIMA - Base",
    "summary": "Module base needed for CCIMA",
    "version": "18.0.0.0.1",
    "category": "Base",
    "license": "OPL-1",
    "depends": [
        "crm",
        "mail",
        "sign",
        "contacts",
        "real_estate_bits",
        "aie_res_partner_extended",
    ],
    "data": [
        "./security/ccima_security.xml",
        "./data/crm_source_items.xml",
        "views/crm_stage_views.xml",
        "views/mail_activity_type_views.xml",
        "views/property_views.xml",
        "views/res_partner_views.xml",
        "./views/crm_lead_view_form.xml",
        "./views/sale_view_order_form_inherit.xml",
        "./views/quick_create_opportunity_form.xml",
        "./views/mail_activity_view_form_popup.xml",
        "./views/mail_activity_schedule_view_form.xml",
    ],
    "support": "luisangel-glez",
    "auto_install": False,
    "installable": True,
}

