{
    'name': 'Solicitudes de Pago con Aprobación',
    'version': '17.0.1.0.0',
    'summary': 'Flujo de aprobación para pagos a proveedores con niveles configurables',
    'description': """
        Módulo para gestionar solicitudes de pago a proveedores.
        - Cualquier empleado puede crear una solicitud
        - Flujo: borrador → enviada → aprobada → pagada (o rechazada)
        - Niveles de aprobación por monto configurables
        - Integración con account.payment al pagar
        - Reporte PDF para archivo
    """,
    'author': 'Binaural',
    'depends': ['account', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/payment_approval_level_views.xml',
        'views/payment_request_views.xml',
        'wizard/payment_request_reject_views.xml',
        'wizard/payment_request_pay_views.xml',
        'report/payment_request_report.xml',
        'report/payment_request_report_template.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
