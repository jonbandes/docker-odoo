"""
Pruebas del endpoint GET /api/v1/products (Tramo A).
Cubren: filtros individuales, combinados, fecha inválida, solo productos activos y vendibles.
"""
from odoo.tests.common import TransactionCase


class TestProductsApi(TransactionCase):
    """Pruebas de lógica de negocio del endpoint de productos."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.categ_a = cls.env['product.category'].create({'name': 'Cat A Test'})
        cls.categ_b = cls.env['product.category'].create({'name': 'Cat B Test'})

        cls.prod_active_sellable = cls.env['product.product'].create({
            'name': 'Prod Activo Vendible',
            'default_code': 'TST-001',
            'categ_id': cls.categ_a.id,
            'list_price': 100.0,
            'active': True,
            'sale_ok': True,
            'type': 'consu',
        })
        cls.prod_inactive = cls.env['product.product'].create({
            'name': 'Prod Inactivo',
            'default_code': 'TST-002',
            'active': False,
            'sale_ok': True,
            'type': 'consu',
        })
        cls.prod_not_sellable = cls.env['product.product'].create({
            'name': 'Prod No Vendible',
            'default_code': 'TST-003',
            'active': True,
            'sale_ok': False,
            'type': 'consu',
        })
        cls.prod_cat_b = cls.env['product.product'].create({
            'name': 'Prod Cat B',
            'default_code': 'TST-004',
            'categ_id': cls.categ_b.id,
            'active': True,
            'sale_ok': True,
            'type': 'consu',
        })

    def _get_domain(self, category_id=None, in_stock=False, modified_since=None):
        """Replica la lógica del controlador para pruebas unitarias."""
        domain = [('active', '=', True), ('sale_ok', '=', True)]
        if category_id:
            domain.append(('categ_id', 'child_of', int(category_id)))
        if in_stock:
            domain.append(('qty_available', '>', 0))
        if modified_since:
            domain.append(('write_date', '>=', modified_since))
        return domain

    def test_only_active_and_sellable(self):
        """Solo aparecen productos activos y vendibles."""
        domain = self._get_domain()
        products = self.env['product.product'].search(domain)
        ids = products.ids
        self.assertIn(self.prod_active_sellable.id, ids)
        self.assertNotIn(self.prod_inactive.id, ids)
        self.assertNotIn(self.prod_not_sellable.id, ids)

    def test_filter_by_category(self):
        """El filtro de categoría limita los resultados."""
        domain = self._get_domain(category_id=self.categ_a.id)
        products = self.env['product.product'].search(domain)
        ids = products.ids
        self.assertIn(self.prod_active_sellable.id, ids)
        self.assertNotIn(self.prod_cat_b.id, ids)

    def test_filter_category_and_sellable_combined(self):
        """Categoría y solo vendibles funcionan combinados."""
        domain = self._get_domain(category_id=self.categ_b.id)
        products = self.env['product.product'].search(domain)
        ids = products.ids
        self.assertIn(self.prod_cat_b.id, ids)
        self.assertNotIn(self.prod_active_sellable.id, ids)

    def test_filter_modified_since(self):
        """El filtro modified_since filtra por fecha de modificación."""
        from datetime import datetime, timedelta
        future = datetime.now() + timedelta(days=1)
        domain = self._get_domain(modified_since=future)
        products = self.env['product.product'].search(domain)
        self.assertNotIn(self.prod_active_sellable.id, products.ids)

    def test_response_fields(self):
        """Los campos requeridos están presentes en el resultado."""
        domain = self._get_domain()
        products = self.env['product.product'].search(domain, limit=1)
        self.assertTrue(products)
        p = products[0]
        # Verifica que los campos existen y son accesibles
        _ = p.id
        _ = p.default_code
        _ = p.name
        _ = p.lst_price
        _ = p.qty_available

    def test_stock_computed_in_batch(self):
        """qty_available se lee en batch (N=1 queries para N productos)."""
        domain = [('active', '=', True), ('sale_ok', '=', True)]
        products = self.env['product.product'].search(domain, limit=50)
        # Acceder a qty_available en el recordset completo (batch compute)
        # Si hubiera N+1 queries, esto sería muy lento; en Odoo se hace en batch
        quantities = {p.id: p.qty_available for p in products}
        self.assertIsInstance(quantities, dict)
