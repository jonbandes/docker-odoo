from odoo import fields, models


class PaymentApprovalLevel(models.Model):
    """Nivel de aprobación: define un monto mínimo y quién aprueba (Tramo B)."""
    _name = 'payment.approval.level'
    _description = 'Nivel de Aprobación de Pago'
    _order = 'amount_min asc'

    name = fields.Char(string='Nombre', required=True)
    amount_min = fields.Float(
        string='Monto mínimo',
        required=True,
        default=0.0,
        help='A partir de este monto, se requiere este nivel de aprobación.',
    )
    approver_id = fields.Many2one(
        'res.users',
        string='Aprobador',
        required=True,
        domain="[('groups_id', 'in', [ref('payment_request.group_payment_request_approver')])]",
    )
    active = fields.Boolean(default=True)

    def _get_approver_for_amount(self, amount):
        """Devuelve el aprobador correspondiente al monto dado."""
        level = self.search(
            [('amount_min', '<=', amount), ('active', '=', True)],
            order='amount_min desc',
            limit=1,
        )
        return level.approver_id if level else self.env['res.users']
