{
    'name': 'Parking Marketplace',
    'version': '1.0',
    'summary': 'A minimal Airbnb-style module for parking spaces.',
    'category': 'Sales',
    'author': 'Jules',
    'website': 'https://www.odoo.com',
    'depends': ['sale_management', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/parking_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
