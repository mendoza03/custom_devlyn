# -*- coding: utf-8 -*-
{
    'name': "ccima_commissions",

    'summary': "ccima_commissions",

    'description': """
ccima_commissions
    """,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','crm','hr','real_estate_bits'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/property_reservation_inherit.xml',
        'views/inherit_employee.xml',
    ],
}

