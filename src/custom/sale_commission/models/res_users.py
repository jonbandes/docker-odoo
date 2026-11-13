from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    commission_rate = fields.Float(
        string='Tasa de comisión (%)',
        default=0.0,
        help='Porcentaje de comisión que se aplica al subtotal de cada línea de pedido.',
    )
