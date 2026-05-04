{
    'name': 'Massive Importer for XLSX',
    'version': '18.0.0.1',
    'description': """ Massive Importer for change values in products from XLSX File

    """,
    'author':'AIE Consulting',
    'depends': ['base', 'sale'],
    'data': [
        './security/ir.model.access.csv',
        './wizard/massive_importter.xml',
    ],
    'qweb': [
        ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'license':'LGPL-3'
}
