{
    'name': 'Inspecciones de Vehículos',
    'version': '17.0.1.0.0',
    'summary': 'Registro de inspecciones de vehículos con checklist',
    'description': """
        Módulo para gestionar inspecciones de vehículos de la flota.
        - Checklist de puntos de inspección (frenos, luces, cauchos…)
        - Flujo de estados: borrador → en curso → aprobada / rechazada
        - Tipo de vehículo: moto, carro, camión, otro
    """,
    'author': 'Binaural',
    'depends': ['fleet', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/fleet_inspection_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
