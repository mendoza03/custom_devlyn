{
    'name': 'Helpdesk Web Form',
    'version': '1.0',
    'depends': ['website', 'helpdesk'],
    'data': [
        'views/helpdesk_form_view.xml',
    ],
    'installable': True,

'assets': {
    'web.assets_frontend': [
        'helpdesk_web_form/static/src/css/helpdesk_main_form.css',
    ],
},
}