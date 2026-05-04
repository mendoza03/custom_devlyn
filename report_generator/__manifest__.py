# -*- coding: utf-8 -*-
{
    'name': "report_generator",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base','ccima_crm_reassign','crm'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/contract_document_views.xml',
        'views/contract_template_views.xml',
        'views/report_contract_document.xml',
        'views/rev_view.xml'
    ],
}

