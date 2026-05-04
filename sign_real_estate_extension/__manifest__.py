# -*- coding: utf-8 -*-
{
    'name': 'Sign Real Estate extension',
    'summary': """
        Module that adds fields from the real_estate_bits module
    """,
    'category': 'Sales',
    'version': '18.0.0.0.1',
    'depends': [
        'base',
        'sale',
        'sign',
        'real_estate_bits',
    ],
    'data': [
        './data/sing_data.xml',
        './views/view_partner_form.xml',
        './views/sign_request_view_form.xml',
        './views/sign_send_request_view_form.xml',
    ],
    'assets': {},
    'external_dependencies': {
        'python': ['loguru'],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'author': 'Dr. Pascual Neftalí Chávez Campos - Github: Cerebellum-ITM',
}
