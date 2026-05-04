# -*- coding: utf-8 -*-
{
    'name': "aie_budget_jobs",

    'summary': "aie_budget_jobs",

    'description': """
aie_budget_jobs
    """,

    'category': 'Administration',
    'version': '18.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'odoo_job_costing_management', 'job_cost_and_estimate_relation', 'aie_master_budget','product','sale','real_state_bits_finance_quote'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/inherit_job_cost.xml',
        'views/inherit_estimate.xml',
        'views/inherit_budget_line.xml',
        'views/inherit_job_cost_line.xml',
        'views/report_master_budget.xml',
        'views/inherit_master_line.xml',
        'views/inherit_loan.xml',
        'views/wizard_subcontracting.xml',
        'views/report_job_costing.xml',
    ],
}

