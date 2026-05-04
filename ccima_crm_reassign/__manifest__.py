# -*- coding: utf-8 -*-
{
    'name': "ccima_crm_reassign",

    'summary': "ccima_crm_reassign",

    'description': """
ccima_crm_reassign
    """,

    "version": "18.0.0.0.1",
    "category": "Hide",
    "license": "OPL-1",

    # any module necessary for this one to work correctly
    'depends': ['base','crm','real_estate_bits','sign','sale','portal','amortization_calculator','web','website','product','crm','mail','hr'],

    # always loaded
    'data': [
        'views/inherit_crm.xml',
        'views/crm_document.xml',
        'security/ir.model.access.csv',
        'views/inherit_condominium.xml',
        'views/inherit_work_site.xml',
        'views/inherit_cluster.xml',
        'views/inherit_property.xml',
        'views/contract_wizard.xml',
        'views/inherit_contract.xml',
        'views/property_map_views.xml',
        'views/property_map_templates.xml',
        'views/rev_crm.xml',
        'views/refound_view.xml',
        'views/request_views.xml',
        'data/cron_actions.xml',
        'views/website_templates.xml',
        'views/cancel_wizard_views.xml',
        'views/docs_wizard.xml',
        'views/payment.xml',
    ],
    'assets': {
            'web.assets_backend': [
                'ccima_crm_reassign/static/src/js/disable_rainbow.js',
            ],
        },
}

