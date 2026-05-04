# -*- coding: utf-8 -*-

{
    'name': 'Master budget',
    'summary': '''
        This is a module to keep the company's budgets in one place.
    ''',
    'category': 'Administration',
    'version': '18.0.0.0.1',
    'depends': [
        'product',
        'project_purchase',
    ],
    'external_dependencies': {
        'python':['loguru', 'openpyxl'],
    },
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizards/master_budget_line_update.xml',
        'views/master_budget_line_views.xml',
        'views/master_budget_views.xml',
        'views/product_template_views.xml',
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'views/purchase_order_views.xml',
        'views/master_budget_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'aie_master_budget/static/src/js/budget_dashboard.js',
            'aie_master_budget/static/src/xml/budget_dashboard.xml',
            'aie_master_budget/static/src/scss/*.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
    'author': "Dr. Pascual Neftalí Chávez Campos - Github: Cerebellum-ITM",
}