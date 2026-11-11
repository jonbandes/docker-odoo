"""
Migración 17.0.2.0.0 — fleet_inspection
Convierte vehicle_type (selección) a vehicle_type_id (many2one).

Escenario:
  1. Instalar versión 17.0.1.0.0 (con vehicle_type como Selection).
  2. Crear inspecciones.
  3. Subir la versión del manifiesto a 17.0.2.0.0 y actualizar con -u fleet_inspection.
  4. Este script corre en post-migrate: vehicle_type_id ya existe en la BD,
     vehicle_type (columna) sigue existiendo porque Odoo nunca borra columnas.

Idempotente: correrlo dos veces no produce duplicados ni cambia datos correctos.
"""

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

VEHICLE_TYPE_MAP = [
    ('moto', 'Moto'),
    ('car', 'Carro'),
    ('truck', 'Camión'),
    ('other', 'Otro'),
]


def migrate(cr, version):
    if not version:
        # Primera instalación: los datos vienen del XML, nada que migrar.
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1. Asegurar que exista el catálogo (idempotente: ON CONFLICT DO NOTHING)
    type_id_by_code = {}
    for code, name in VEHICLE_TYPE_MAP:
        vtype = env['fleet.inspection.vehicle.type'].search([('code', '=', code)], limit=1)
        if not vtype:
            vtype = env['fleet.inspection.vehicle.type'].create({'name': name, 'code': code})
            _logger.info('fleet_inspection migrate: creado tipo "%s" (code=%s)', name, code)
        type_id_by_code[code] = vtype.id

    # 2. Mapear inspecciones cuyo vehicle_type_id aún no está asignado
    for code, type_id in type_id_by_code.items():
        cr.execute(
            """
            UPDATE fleet_inspection
               SET vehicle_type_id = %s
             WHERE vehicle_type = %s
               AND (vehicle_type_id IS NULL OR vehicle_type_id != %s)
            """,
            [type_id, code, type_id],
        )
        rows = cr.rowcount
        if rows:
            _logger.info(
                'fleet_inspection migrate: %d inspección(es) actualizadas para tipo "%s"',
                rows, code,
            )

    # 3. Verificar que no quedaron inspecciones sin tipo
    cr.execute(
        "SELECT COUNT(*) FROM fleet_inspection WHERE vehicle_type_id IS NULL"
    )
    orphans = cr.fetchone()[0]
    if orphans:
        _logger.warning(
            'fleet_inspection migrate: %d inspección(es) sin vehicle_type_id. '
            'Revise manualmente.',
            orphans,
        )
    else:
        _logger.info('fleet_inspection migrate: todas las inspecciones tienen vehicle_type_id.')
