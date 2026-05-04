{
    'name': 'Real State Financer Quote',
    'version': '18.0.0.1',
    'description': """ Financing Quoter for Real State Bits addon

    """,
    'author':'AIE Consulting',
    'depends': ['base', 'portal','real_estate_bits','web'],
    'data': [
        './data/mail_template_reservation.xml',
        './data/ir_cron.xml',
        './security/ir.model.access.csv',
        './views/sale_order_view.xml',
        './views/property_contract.xml',
        './views/sale_portal_templates.xml',
        './views/property_reservation.xml',
        './views/property_promotions.xml',
        './views/product_template.xml',
        './wizards/make_payment_to_capital_wizard.xml',
        './reports/sale_order_inherit_report.xml',
    ],
    'qweb': [
        ],
    'assets': {
        'web.assets_frontend': [
            'real_state_bits_finance_quote/static/src/js/signature_form_override.js',
        ],
    },
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'external_dependencies':{
        'python':['numpy_financial']
    },
    'license':'LGPL-3'
}
