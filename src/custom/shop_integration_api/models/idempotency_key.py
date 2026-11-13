from odoo import fields, models


class ShopIdempotencyKey(models.Model):
    """Almacena las claves de idempotencia para evitar pedidos duplicados (Tramo C)."""
    _name = 'shop.idempotency.key'
    _description = 'Clave de idempotencia de la API'
    _log_access = False

    key = fields.Char(string='Idempotency-Key', required=True, index=True)
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    body_hash = fields.Char(string='Hash del cuerpo', required=True, size=64)
    created_at = fields.Datetime(default=fields.Datetime.now, required=True)

    _sql_constraints = [
        ('key_user_unique', 'UNIQUE(key, user_id)',
         'La clave de idempotencia debe ser única por usuario.'),
    ]
