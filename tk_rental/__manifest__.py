# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
{
    'name': "Advance Equipment Rental Management | Equipment Lease | Rental Management",
    'version': "1.8",
    'description': "Rental",
    'category': "sale",
    'summary': "Advance Equipment Rental Management ",
    'author': 'TechKhedut Inc.',
    'website': "https://techkhedut.com",
    'depends': ['mail',
                'contacts',
                'sale_management',
                'stock',
                'maintenance'
                ],
    'data': [
        # data
        'data/sequence_views.xml',
        # Security
        'security/ir.model.access.csv',
        # Reports
        'report/quotation_report.xml',
        'report/return_order_details_report.xml',
        # Wizards
        'wizards/update_last_odometer_wizard_views.xml',
        # Views
        'views/assets.xml',
        'views/rent_order_views.xml',
        'views/rent_term_views.xml',
        'views/renting_items_views.xml',
        'views/product_inherit_views.xml',
        'views/invoice_inherit_views.xml',
        'views/stock_picking_inherit_views.xml',
        'views/maintenance_inherit_views.xml',
        'views/equipment_odometer_views.xml',
        # data
        'data/rental_quotation_mail_template.xml',
        'data/return_damage_charges_mail_template.xml',
        # Menus
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'tk_rental/static/src/xml/template.xml',
            'tk_rental/static/src/scss/style.scss',
            'tk_rental/static/src/js/lib/apexcharts.js',
            'tk_rental/static/src/js/other/rental_dashboard.js',
        ],
    },
    'images': ['static/description/banner.gif'],
    'price': 149,
    'currency': 'USD',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
}
