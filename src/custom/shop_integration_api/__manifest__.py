{
    'name': 'Integración API Tienda en Línea',
    'version': '17.0.1.0.0',
    'summary': 'Endpoints REST para consultar productos y crear pedidos desde la tienda',
    'description': """
        Expone endpoints REST para que la tienda en línea del cliente consulte
        productos con stock y cree pedidos de venta en Odoo.

        Tramo A: GET /api/v1/products (auth de sesión)
        Tramo B: Bearer token + POST /api/v1/orders + log de llamadas
        Tramo C: Paginación + Idempotency-Key + webhook de entrega
    """,
    'author': 'Binaural',
    'depends': ['sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/api_log_views.xml',
        'views/webhook_config_views.xml',
        'data/ir_sequence.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
