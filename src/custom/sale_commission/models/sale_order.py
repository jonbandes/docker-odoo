from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        # Validar que el usuario tenga permiso de gestión de comisiones
        # antes de confirmar para garantizar que las comisiones estén configuradas
        if not self.env.user.has_group('sale_commission.group_sale_commission_manager'):
            raise UserError(
                _('Solo el gestor de comisiones puede confirmar pedidos de venta. '
                  'Contacte a su gerente.')
            )
        return super().action_confirm()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    commission_rate = fields.Float(
        string='Comisión (%)',
        compute='_compute_commission',
        store=True,
        digits=(5, 2),
    )
    commission_amount = fields.Monetary(
        string='Importe comisión',
        compute='_compute_commission',
        store=True,
        currency_field='currency_id',
    )

    @api.depends('order_id.user_id', 'order_id.user_id.commission_rate', 'price_subtotal')
    def _compute_commission(self):
        for line in self:
            rate = line.order_id.user_id.commission_rate or 0.0
            line.commission_rate = rate
            line.commission_amount = line.price_subtotal * rate / 100.0
