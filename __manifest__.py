# -*- encoding: utf-8 -*-

{
    'name': 'FEL Infile',
    'version': '1.2',
    'category': 'Custom',
    'description': """ Integración con factura electrónica de Infile """,
    'author': 'aquíH',
    'website': 'http://aquih.com/',
    'depends': ['fel_gt'],
    'data': [
        'views/account_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [],
    'installable': True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
