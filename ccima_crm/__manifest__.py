# -*- coding: utf-8 -*-

{
    'name': 'CCIMA CRM',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Stage validations for CRM',
    'description': """
        CCIMA CRM Module
        ================
        Adds stage validations and progressive fields for CRM opportunities.
    """,
    'author': 'CCIMA',
    'website': 'https://www.ccima.com',
    'depends': ['ccima_crm_reassign', 'product', 'sale_crm'],
    'data': [
        'views/crm_lead_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
