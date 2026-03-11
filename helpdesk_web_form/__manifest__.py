{
    'name': 'Helpdesk Web Form',
    'version': '1.0',
    'depends': ['website', 'helpdesk', 'helpdesk_custom_datos'],
    'data': [
        'views/helpdesk_form_view.xml',
        'views/helpdesk_success_template.xml',
    ],
    'installable': True,

'assets': {
    'web.assets_frontend': [
        'helpdesk_web_form/static/src/css/helpdesk_main_form.css',
        'helpdesk_web_form/static/src/js/index.js',
    ],
},
}