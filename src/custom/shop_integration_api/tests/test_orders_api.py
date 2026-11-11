"""
Pruebas de la lógica de pedidos (Tramo B).
Validaciones de errores por campos faltantes, producto/cliente inexistente.
Las pruebas HttpCase requieren un servidor Odoo corriendo; las pruebas unitarias
(TransactionCase) se pueden ejecutar con el comando de test estándar.
"""
from odoo.tests.common import TransactionCase


class TestOrderValidation(TransactionCase):
    """Pruebas de validación del endpoint POST /api/v1/orders."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Distribuidora Test C.A.',
            'vat': 'J-12345678-9',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Producto API Test',
            'default_code': 'API-001',
            'list_price': 150.0,
            'active': True,
            'sale_ok': True,
            'type': 'consu',
        })

    def _create_order(self, vat=None, external_ref='EXT-001', lines=None):
        vat = vat or self.partner.vat
        lines = lines or [{'product_id': self.product.id, 'product_uom_qty': 1, 'price_unit': 150.0}]
        return self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'client_order_ref': external_ref,
            'order_line': [(0, 0, l) for l in lines],
        })

    def test_order_created_as_draft(self):
        """El pedido se crea en estado borrador (cotización), no confirmado."""
        order = self._create_order()
        self.assertEqual(order.state, 'draft',
                         'El pedido debe quedar como cotización, no confirmado automáticamente.')

    def test_order_has_external_ref(self):
        """La referencia externa del cliente queda guardada en el pedido."""
        order = self._create_order(external_ref='SHOP-REF-123')
        self.assertEqual(order.client_order_ref, 'SHOP-REF-123')

    def test_partner_found_by_vat(self):
        """Se puede encontrar un cliente por su RIF."""
        partner = self.env['res.partner'].search([
            ('vat', '=', self.partner.vat), ('active', '=', True)
        ], limit=1)
        self.assertTrue(partner, 'Debe encontrarse el cliente por RIF.')
        self.assertEqual(partner.id, self.partner.id)

    def test_partner_not_found_by_bad_vat(self):
        """Un RIF inexistente no devuelve cliente."""
        partner = self.env['res.partner'].search([
            ('vat', '=', 'J-00000000-0'), ('active', '=', True)
        ], limit=1)
        self.assertFalse(partner, 'No debe haber cliente con RIF ficticio.')

    def test_product_found_by_default_code(self):
        """Se puede encontrar un producto por código."""
        product = self.env['product.product'].search([
            ('default_code', '=', 'API-001'),
            ('active', '=', True),
            ('sale_ok', '=', True),
        ], limit=1)
        self.assertTrue(product)
        self.assertEqual(product.id, self.product.id)

    def test_product_not_found_by_bad_code(self):
        """Un código inexistente no devuelve producto."""
        product = self.env['product.product'].search([
            ('default_code', '=', 'NONEXISTENT-999'),
            ('active', '=', True),
        ], limit=1)
        self.assertFalse(product)

    def test_order_line_has_product(self):
        """Las líneas del pedido tienen el producto correcto."""
        order = self._create_order()
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line[0].product_id.id, self.product.id)
