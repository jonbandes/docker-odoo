import json
from odoo import models


class StockPicking(models.Model):
    """Tramo C: encola un webhook cuando se valida una entrega ligada a un pedido."""
    _inherit = 'stock.picking'

    def button_validate(self):
        result = super().button_validate()
        # Encola el webhook en segundo plano para no bloquear al usuario
        self._enqueue_delivery_webhook()
        return result

    def _enqueue_delivery_webhook(self):
        configs = self.env['shop.webhook.config'].sudo().search([('active', '=', True)])
        if not configs:
            return
        for picking in self:
            if picking.picking_type_code != 'outgoing':
                continue
            sale = picking.sale_id
            if not sale:
                continue
            payload = {
                'event': 'delivery.validated',
                'picking_id': picking.id,
                'picking_name': picking.name,
                'sale_order': sale.name,
                'partner_vat': sale.partner_id.vat or '',
                'external_ref': sale.client_order_ref or '',
            }
            for config in configs:
                self.env['shop.webhook.queue'].sudo().create({
                    'config_id': config.id,
                    'event': 'delivery.validated',
                    'payload': json.dumps(payload),
                    'picking_id': picking.id,
                })
