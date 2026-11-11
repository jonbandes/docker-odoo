{
    'name': 'Inspecciones de Vehículos',
    'version': '17.0.2.0.0',
    'summary': 'Registro de inspecciones de vehículos con checklist',
    'description': """
        Módulo para gestionar inspecciones de vehículos de la flota.
        - Checklist de puntos de inspección (frenos, luces, cauchos…)
        - Flujo de estados: borrador → en curso → aprobada / rechazada
        - Catálogo de tipos de vehículo (many2one)
    """,
    'author': 'Binaural',
    'depends': ['fleet', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/fleet_inspection_vehicle_type.xml',
        'views/fleet_inspection_views.xml',
        'views/fleet_inspection_vehicle_type_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
