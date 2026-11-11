import requests as http_requests
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class ShopWebhookConfig(models.Model):
    """Configuración del webhook hacia la tienda (Tramo C)."""
    _name = 'shop.webhook.config'
    _description = 'Configuración de webhook de la tienda'

    name = fields.Char(string='Nombre', required=True)
    url = fields.Char(string='URL del webhook', required=True)
    active = fields.Boolean(default=True)
    secret = fields.Char(
        string='Secret',
        help='Valor enviado en cabecera X-Webhook-Secret para que la tienda valide la fuente.',
        groups='base.group_system',
    )
    max_retries = fields.Integer(string='Reintentos máximos', default=3)
    timeout_seconds = fields.Integer(string='Timeout (s)', default=10)


class ShopWebhookQueue(models.Model):
    """Cola de webhooks pendientes de enviar. Un cron los procesa en segundo plano."""
    _name = 'shop.webhook.queue'
    _description = 'Cola de webhooks pendientes'
    _order = 'create_date asc'

    config_id = fields.Many2one('shop.webhook.config', required=True, ondelete='cascade')
    event = fields.Char(string='Evento', required=True)
    payload = fields.Text(string='Payload JSON', required=True)
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('done', 'Enviado'),
        ('failed', 'Fallido'),
    ], default='pending', required=True, index=True)
    attempts = fields.Integer(default=0)
    last_error = fields.Text(string='Último error')
    picking_id = fields.Many2one('stock.picking', string='Entrega', ondelete='set null')

    def _process_pending(self):
        """Llamado por ir.cron para enviar webhooks pendientes."""
        pending = self.search([('state', '=', 'pending')])
        for item in pending:
            item._send()

    def _send(self):
        self.ensure_one()
        config = self.config_id
        headers = {'Content-Type': 'application/json'}
        if config.secret:
            headers['X-Webhook-Secret'] = config.secret
        try:
            resp = http_requests.post(
                config.url,
                data=self.payload,
                headers=headers,
                timeout=config.timeout_seconds,
            )
            resp.raise_for_status()
            self.write({'state': 'done', 'attempts': self.attempts + 1})
        except Exception as exc:
            self.write({
                'attempts': self.attempts + 1,
                'last_error': str(exc)[:1000],
                'state': 'failed' if self.attempts + 1 >= config.max_retries else 'pending',
            })
            _logger.warning('shop_integration_api webhook failed (%s): %s', self.id, exc)
