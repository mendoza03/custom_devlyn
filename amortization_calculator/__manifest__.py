# -*- coding: utf-8 -*-
{
    'name': "amortization_calculator",

    'summary': "amortization_calculator",

    'description': """
amortization_calculator
    """,

    'author': "MiguelMendoza",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base','crm','real_estate_bits','account_accountant','account','real_state_bits_finance_quote'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/amortization_calculator.xml',
        'views/acciones.xml',
        'views/report.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'amortization_calculator/static/src/css/amortization.css',
        ],
    },

}

