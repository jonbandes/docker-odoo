from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestFleetInspection(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vehicle = cls.env['fleet.vehicle'].create({
            'model_id': cls.env['fleet.vehicle.model'].create({
                'name': 'Modelo Prueba',
                'brand_id': cls.env['fleet.vehicle.model.brand'].create({'name': 'Marca Prueba'}).id,
            }).id,
            'license_plate': 'TST-001',
        })

    def _make_vehicle_type(self, code='car'):
        """Busca o crea el tipo de vehículo (compatibilidad Tramo A y B)."""
        if 'vehicle_type_id' in self.env['fleet.inspection']._fields:
            vtype = self.env['fleet.inspection.vehicle.type'].search([('code', '=', code)], limit=1)
            if not vtype:
                names = {'moto': 'Moto', 'car': 'Carro', 'truck': 'Camión', 'other': 'Otro'}
                vtype = self.env['fleet.inspection.vehicle.type'].create({
                    'name': names.get(code, code),
                    'code': code,
                })
            return vtype
        return None

    def _create_inspection(self, vehicle_type_code='car'):
        vals = {
            'name': 'INS/TEST/001',
            'vehicle_id': self.vehicle.id,
            'date': '2026-11-11',
        }
        if 'vehicle_type_id' in self.env['fleet.inspection']._fields:
            vals['vehicle_type_id'] = self._make_vehicle_type(vehicle_type_code).id
        else:
            vals['vehicle_type'] = vehicle_type_code
        return self.env['fleet.inspection'].create(vals)

    def test_initial_state_is_draft(self):
        """Nueva inspección comienza en borrador."""
        inspection = self._create_inspection()
        self.assertEqual(inspection.state, 'draft')

    def test_flow_draft_to_in_progress(self):
        """Acción Iniciar mueve a en curso."""
        inspection = self._create_inspection()
        inspection.action_start()
        self.assertEqual(inspection.state, 'in_progress')

    def test_flow_in_progress_to_approved(self):
        """Aprobar desde en curso funciona si todos los puntos pasan."""
        inspection = self._create_inspection()
        inspection.action_start()
        self.env['fleet.inspection.point'].create({
            'inspection_id': inspection.id,
            'name': 'Frenos',
            'result': 'pass',
        })
        inspection.action_approve()
        self.assertEqual(inspection.state, 'approved')

    def test_cannot_approve_with_failed_point(self):
        """No se puede aprobar si hay un punto fallido."""
        inspection = self._create_inspection()
        inspection.action_start()
        self.env['fleet.inspection.point'].create({
            'inspection_id': inspection.id,
            'name': 'Luces',
            'result': 'fail',
        })
        with self.assertRaises(ValidationError):
            inspection.action_approve()

    def test_reject_requires_reason(self):
        """Rechazar sin motivo lanza ValidationError."""
        inspection = self._create_inspection()
        inspection.action_start()
        with self.assertRaises(ValidationError):
            inspection.action_reject()

    def test_reject_with_reason(self):
        """Rechazar con motivo cambia estado a rechazada."""
        inspection = self._create_inspection()
        inspection.action_start()
        inspection.rejection_reason = 'Daños graves en carrocería'
        inspection.action_reject()
        self.assertEqual(inspection.state, 'rejected')

    def test_all_vehicle_types_selection(self):
        """Tramo A: todos los tipos de selección son aceptados."""
        if 'vehicle_type_id' in self.env['fleet.inspection']._fields:
            self.skipTest('Tramo B instalado: vehicle_type es many2one')
        for vtype in ('moto', 'car', 'truck', 'other'):
            inspection = self._create_inspection(vehicle_type_code=vtype)
            self.assertEqual(inspection.vehicle_type, vtype)

    def test_all_vehicle_types_many2one(self):
        """Tramo B: todos los tipos del catálogo son aceptados."""
        if 'vehicle_type_id' not in self.env['fleet.inspection']._fields:
            self.skipTest('vehicle_type_id no existe (versión Tramo A)')
        for code in ('moto', 'car', 'truck', 'other'):
            inspection = self._create_inspection(vehicle_type_code=code)
            self.assertEqual(inspection.vehicle_type_id.code, code)

    def test_migration_logic(self):
        """Tramo B: la lógica de migración asigna vehicle_type_id correcto.

        Simula el escenario: inspección creada con code='car' en BD,
        después del UPDATE de migración debe apuntar al tipo correcto.
        """
        if 'vehicle_type_id' not in self.env['fleet.inspection']._fields:
            self.skipTest('vehicle_type_id no existe (versión Tramo A)')

        # Asegurar que el catálogo existe
        car_type = self._make_vehicle_type('car')
        self.assertTrue(car_type, 'El tipo Carro debe existir en el catálogo')

        # Crear una inspección correctamente con Tramo B
        inspection = self._create_inspection('car')
        self.assertEqual(inspection.vehicle_type_id.code, 'car')

        # Simular que el script SQL de migración actualiza un registro sin tipo
        self.env.cr.execute(
            "UPDATE fleet_inspection SET vehicle_type_id = NULL WHERE id = %s",
            [inspection.id],
        )
        inspection.invalidate_recordset()
        self.assertFalse(inspection.vehicle_type_id)

        # Ejecutar la lógica de migración sobre este registro
        from odoo import api, SUPERUSER_ID
        env = api.Environment(self.env.cr, SUPERUSER_ID, {})
        type_map = {}
        for code in ('moto', 'car', 'truck', 'other'):
            vt = env['fleet.inspection.vehicle.type'].search([('code', '=', code)], limit=1)
            if vt:
                type_map[code] = vt.id

        for code, type_id in type_map.items():
            self.env.cr.execute(
                """UPDATE fleet_inspection
                      SET vehicle_type_id = %s
                    WHERE vehicle_type = %s AND vehicle_type_id IS NULL""",
                [type_id, code],
            )

        inspection.invalidate_recordset()
        self.assertEqual(
            inspection.vehicle_type_id.code, 'car',
            'La migración debe asignar vehicle_type_id = car',
        )
