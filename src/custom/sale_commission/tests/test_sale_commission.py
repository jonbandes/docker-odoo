from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSaleCommission(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Producto Prueba Comisión',
            'list_price': 200.0,
            'type': 'consu',
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Cliente Prueba Comisión',
        })
        # Vendedor sin grupo de gestor de comisiones
        cls.salesperson = cls.env['res.users'].create({
            'name': 'Vendedor Prueba',
            'login': 'vendedor_commission_test@binaural.test',
            'email': 'vendedor_commission_test@binaural.test',
            'groups_id': [(4, cls.env.ref('sales_team.group_sale_salesman').id)],
            'commission_rate': 5.0,
        })

    def _create_order(self, user=None):
        user = user or self.salesperson
        return self.env['sale.order'].with_user(user).create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 200.0,
            })],
        })

    def test_commission_calculated_from_user_rate(self):
        """La comisión se calcula según la tasa del vendedor."""
        order = self._create_order()
        line = order.order_line[0]
        self.assertAlmostEqual(line.commission_rate, 5.0)
        self.assertAlmostEqual(line.commission_amount, 20.0)  # 400 * 5% = 20

    def test_commission_zero_when_no_rate(self):
        """Sin tasa configurada, la comisión es cero."""
        self.salesperson.commission_rate = 0.0
        order = self._create_order()
        line = order.order_line[0]
        self.assertAlmostEqual(line.commission_amount, 0.0)
        # Reset
        self.salesperson.commission_rate = 5.0

    def test_salesperson_can_confirm_order(self):
        """T-200: el vendedor (sin grupo gestor) debe poder confirmar pedidos.

        Esta prueba FALLA en la versión con el bug (el override de action_confirm
        bloquea a usuarios sin group_sale_commission_manager) y PASA con la corrección.
        """
        order = self._create_order()
        # No debe lanzar UserError
        order.with_user(self.salesperson).action_confirm()
        self.assertEqual(
            order.state, 'sale',
            'El vendedor debe poder confirmar pedidos sin ser gestor de comisiones.',
        )

    def test_manager_can_also_confirm_order(self):
        """El gestor de comisiones también debe poder confirmar pedidos."""
        manager = self.env['res.users'].create({
            'name': 'Gerente Comisiones',
            'login': 'gerente_commission_test@binaural.test',
            'email': 'gerente_commission_test@binaural.test',
            'groups_id': [
                (4, self.env.ref('sales_team.group_sale_salesman').id),
                (4, self.env.ref('sale_commission.group_sale_commission_manager').id),
            ],
            'commission_rate': 10.0,
        })
        order = self._create_order(user=manager)
        order.with_user(manager).action_confirm()
        self.assertEqual(order.state, 'sale')

    def test_commission_updates_on_subtotal_change(self):
        """La comisión se recalcula al cambiar el subtotal."""
        order = self._create_order()
        line = order.order_line[0]
        line.price_unit = 500.0
        self.assertAlmostEqual(line.commission_amount, 50.0)  # 1000 * 5% = 50
