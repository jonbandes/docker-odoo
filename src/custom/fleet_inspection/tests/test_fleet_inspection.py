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

    def _create_inspection(self, vehicle_type='car'):
        return self.env['fleet.inspection'].create({
            'name': 'INS/TEST/001',
            'vehicle_id': self.vehicle.id,
            'vehicle_type': vehicle_type,
            'date': '2026-11-11',
        })

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

    def test_all_vehicle_types(self):
        """Todos los tipos de vehículo son aceptados."""
        for vtype in ('moto', 'car', 'truck', 'other'):
            inspection = self._create_inspection(vehicle_type=vtype)
            self.assertEqual(inspection.vehicle_type, vtype)

    def test_migration_vehicle_type_id(self):
        """Tramo B: vehicle_type_id se asigna en la migración.

        Esta prueba verifica la lógica de migración: dado un registro con vehicle_type
        (selección), después de la migración debe tener vehicle_type_id apuntando
        al registro correcto del catálogo.
        """
        # Solo corre si vehicle_type_id existe (versión 17.0.2.0.0)
        if 'vehicle_type_id' not in self.env['fleet.inspection']._fields:
            self.skipTest('vehicle_type_id no existe (Tramo A, pre-migración Tramo B)')

        from odoo.addons.fleet_inspection.migrations._17_0_2_0_0 import post_migrate
        # El catálogo debe haberse creado en la instalación
        car_type = self.env['fleet.inspection.vehicle.type'].search([('code', '=', 'car')])
        self.assertTrue(car_type, 'El tipo de vehículo "Carro" debe existir en el catálogo')

        inspection = self._create_inspection(vehicle_type='car')
        # Simula la migración sobre este registro
        post_migrate.migrate(self.env.cr, '17.0.1.0.0')
        inspection.invalidate_recordset()
        self.assertEqual(
            inspection.vehicle_type_id.code, 'car',
            'La migración debe asignar vehicle_type_id correcto',
        )
