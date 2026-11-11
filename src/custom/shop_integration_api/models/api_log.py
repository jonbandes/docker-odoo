from odoo import fields, models


class ShopApiLog(models.Model):
    """Registro de cada llamada a la API (éxito y error). No almacena la clave."""
    _name = 'shop.api.log'
    _description = 'Log de llamadas a la API de la tienda'
    _order = 'create_date desc'
    _log_access = False  # Usamos campos propios para fechas

    endpoint = fields.Char(string='Endpoint', required=True, index=True)
    method = fields.Char(string='Método HTTP', size=8, required=True)
    user_id = fields.Many2one('res.users', string='Usuario', ondelete='set null', index=True)
    response_code = fields.Integer(string='Código HTTP', required=True, index=True)
    duration_ms = fields.Float(string='Duración (ms)', digits=(10, 2))
    request_ref = fields.Char(
        string='Referencia externa',
        help='Valor de Idempotency-Key o referencia del pedido.',
    )
    error_code = fields.Char(string='Código de error')
    timestamp = fields.Datetime(
        string='Fecha/hora',
        default=fields.Datetime.now,
        required=True,
        index=True,
    )

    def _log(self, endpoint, method, user_id, response_code, duration_ms,
             request_ref=None, error_code=None):
        """Crea un registro de log. Se llama con sudo() para no depender del usuario."""
        self.sudo().create({
            'endpoint': endpoint,
            'method': method,
            'user_id': user_id,
            'response_code': response_code,
            'duration_ms': duration_ms,
            'request_ref': request_ref,
            'error_code': error_code,
        })
