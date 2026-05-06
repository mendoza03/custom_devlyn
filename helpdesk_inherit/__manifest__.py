{
    'name': 'Helpdesk Cancel Reasons',
    'version': '19.0.1.0.0',
    'category': 'Helpdesk',
    'summary': 'Cancel helpdesk tickets using configured cancellation reasons',
    'description': '''
Helpdesk Cancel Reasons
=======================

Adds a professional cancellation flow for Helpdesk tickets:
- Configurable cancellation reasons.
- Dedicated security group.
- Cancellation wizard.
- Logged-in cancellation user.
- Cancellation date.
- Internal cancellation note.
- Chatter audit log.
- Validation to avoid cancelling already cancelled tickets.
    ''',
    'author': 'Custom',
    'license': 'LGPL-3',
    'depends': [
        'helpdesk',
        'mail',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/cancel_reason_views.xml',
        'views/helpdesk_ticket_views.xml',
        'wizard/cancel_ticket_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
