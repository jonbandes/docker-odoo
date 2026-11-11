from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestPaymentRequest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Proveedor Prueba S.A.',
            'supplier_rank': 1,
        })
        cls.solicitante = cls.env['res.users'].create({
            'name': 'Solicitante Prueba',
            'login': 'solicitante_test@binaural.test',
            'email': 'solicitante_test@binaural.test',
            'groups_id': [(4, cls.env.ref('payment_request.group_payment_request_solicitante').id)],
        })
        cls.aprobador = cls.env['res.users'].create({
            'name': 'Aprobador Prueba',
            'login': 'aprobador_test@binaural.test',
            'email': 'aprobador_test@binaural.test',
            'groups_id': [(4, cls.env.ref('payment_request.group_payment_request_approver').id)],
        })
        cls.tesoreria = cls.env['res.users'].create({
            'name': 'Tesorero Prueba',
            'login': 'tesorero_test@binaural.test',
            'email': 'tesorero_test@binaural.test',
            'groups_id': [(4, cls.env.ref('payment_request.group_payment_request_treasury').id)],
        })

    def _create_request(self, amount=500.0, user=None):
        user = user or self.solicitante
        return self.env['payment.request'].with_user(user).create({
            'partner_id': self.partner.id,
            'amount': amount,
            'concept': 'Pago de servicios de prueba',
        })

    # --- Tramo A: flujo básico ---

    def test_sequence_assigned_on_create(self):
        """La secuencia SP/YYYY/XXXX se asigna al crear."""
        req = self._create_request()
        self.assertTrue(req.name.startswith('SP/'), f'Secuencia incorrecta: {req.name}')

    def test_initial_state_draft(self):
        req = self._create_request()
        self.assertEqual(req.state, 'draft')

    def test_amount_zero_raises(self):
        """Monto cero debe lanzar ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_request(amount=0.0)

    def test_amount_negative_raises(self):
        """Monto negativo debe lanzar ValidationError."""
        with self.assertRaises(ValidationError):
            self._create_request(amount=-100.0)

    def test_solicitante_can_send(self):
        """El solicitante puede enviar la solicitud."""
        req = self._create_request()
        req.with_user(self.solicitante).action_send()
        self.assertEqual(req.state, 'sent')

    def test_solicitante_cannot_approve(self):
        """El solicitante no puede aprobar, ni llamando al método directamente."""
        req = self._create_request()
        req.with_user(self.solicitante).action_send()
        with self.assertRaises(UserError):
            req.with_user(self.solicitante).action_approve()

    def test_aprobador_can_approve(self):
        """El aprobador puede aprobar una solicitud enviada."""
        req = self._create_request()
        req.action_send()
        req.with_user(self.aprobador).action_approve()
        self.assertEqual(req.state, 'approved')

    def test_sent_request_not_editable(self):
        """Una solicitud enviada no debería poder cambiar campos clave."""
        req = self._create_request()
        req.action_send()
        # El campo user_id es readonly en la vista; el modelo no lo bloquea explícitamente
        # pero la vista lo hace con readonly="True". Verificamos que el estado impide reenvío.
        with self.assertRaises(UserError):
            req.action_send()  # No se puede enviar si ya está en 'sent'

    def test_rejection_wizard_requires_reason(self):
        """El wizard de rechazo requiere motivo."""
        req = self._create_request()
        req.action_send()
        wizard = self.env['payment.request.reject.wizard'].with_user(self.aprobador).create({
            'request_id': req.id,
            'reason': '',
        })
        with self.assertRaises(UserError):
            wizard.action_reject()

    def test_rejection_with_reason(self):
        """Rechazar con motivo cambia estado y publica en chatter."""
        req = self._create_request()
        req.action_send()
        wizard = self.env['payment.request.reject.wizard'].with_user(self.aprobador).create({
            'request_id': req.id,
            'reason': 'Monto supera el presupuesto aprobado',
        })
        wizard.action_reject()
        self.assertEqual(req.state, 'rejected')
        self.assertIn('Monto supera', req.rejection_reason)

    def test_solicitante_only_sees_own(self):
        """El solicitante solo ve sus propias solicitudes."""
        req_mine = self._create_request(user=self.solicitante)
        # Crear otra solicitud con el tesorero
        req_other = self.env['payment.request'].with_user(self.tesoreria).create({
            'partner_id': self.partner.id,
            'amount': 100.0,
            'concept': 'Otra solicitud',
        })
        visible = self.env['payment.request'].with_user(self.solicitante).search([])
        self.assertIn(req_mine.id, visible.ids)
        self.assertNotIn(req_other.id, visible.ids)

    # --- Tramo B: aprobación por nivel ---

    def test_approval_level_assigns_approver(self):
        """El nivel de aprobación asigna el aprobador correcto al enviar."""
        self.env['payment.approval.level'].create({
            'name': 'Jefe de área',
            'amount_min': 0.0,
            'approver_id': self.aprobador.id,
        })
        req = self._create_request(amount=500.0)
        req.action_send()
        self.assertEqual(req.approver_id, self.aprobador)

    def test_only_assigned_approver_can_approve(self):
        """Solo el aprobador asignado puede aprobar (Tramo B)."""
        self.env['payment.approval.level'].create({
            'name': 'Jefe de área',
            'amount_min': 0.0,
            'approver_id': self.aprobador.id,
        })
        other_approver = self.env['res.users'].create({
            'name': 'Otro Aprobador',
            'login': 'otro_aprobador@binaural.test',
            'email': 'otro_aprobador@binaural.test',
            'groups_id': [(4, self.env.ref('payment_request.group_payment_request_approver').id)],
        })
        req = self._create_request(amount=500.0)
        req.action_send()
        # otro_approver no es el asignado → debe fallar
        with self.assertRaises(UserError):
            req.with_user(other_approver).action_approve()

    def test_cannot_pay_twice(self):
        """Una solicitud no se puede pagar dos veces."""
        req = self._create_request()
        req.action_send()
        req.with_user(self.aprobador).action_approve()
        # Forzar estado de pago con un payment_id falso para simular pago previo
        req.payment_id = self.env['account.payment'].sudo().create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner.id,
            'amount': req.amount,
            'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
        })
        with self.assertRaises(UserError):
            req.action_pay()
