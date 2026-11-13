{
    'name': 'Comisiones de Ventas',
    'version': '17.0.1.0.0',
    'summary': 'Calcula comisiones del vendedor por línea de pedido de venta',
    'description': """
        Módulo para el cálculo automático de comisiones de vendedores.
        - Tasa de comisión configurada por usuario
        - Cálculo automático por línea de pedido
        - Reporte mensual por vendedor
    """,
    'author': 'Binaural',
    'depends': ['sale'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_users_views.xml',
        'views/sale_order_views.xml',
        'report/commission_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
