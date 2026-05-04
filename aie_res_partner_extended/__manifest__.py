# -*- coding: utf-8 -*-
{
    'name': 'res partner extended',
    'summary': '''
        This module adds customizations to the res.partner model as the cities of Mexico
    ''',
    'category': 'Hidden',
    'version': '18.0.0.0.1',
    'depends': [
        'contacts',
    ],
    'data': [
        './security/ir.model.access.csv',
        './data/res.custom.city.csv',
    ],
    'assets': {

    },
    'external_dependencies': {
        'python':[],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'author': "Dr. Pascual Neftalí Chávez Campos - Github: Cerebellum-ITM",
}

