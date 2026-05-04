# -*- coding: utf-8 -*-
{
    'name': "ccima_energy",

    'summary': "ccima_energy",

    'description': """
ccima_energy
    """,

    'category': 'Administration',
    'version': '18.0.0.0.1',


    # any module necessary for this one to work correctly
    'depends': ['base','sale','purchase','product'],

    'data': [
        'views/inherit_product.xml',
    ],

}

