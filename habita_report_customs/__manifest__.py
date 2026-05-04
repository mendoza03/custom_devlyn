{
    'name': 'Habitat Rerport Customs',
    'version': '18.0.0.1',
    'description': """ Customization for Sale Order PDF Report and QWEB View

    """,
    'author': 'AIE Consulting',
    'depends': [
        'base',
        'portal',
        'sale',
        'sale_stock',
        'real_state_bits_finance_quote',
    ],
    'data': [
        './report/sale_order_report.xml',
        './views/portal_sale_order.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'habita_report_customs/static/src/css/portal_quotation_style.css'
        ],
    },
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
