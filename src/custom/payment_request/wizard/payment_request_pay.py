from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PaymentRequestPayWizard(models.TransientModel):
    _name = 'payment.request.pay.wizard'
    _description = 'Asistente de Pago de Solicitud'

    request_id = fields.Many2one(
        'payment.request',
        string='Solicitud',
        required=True,
        readonly=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario de pago',
        required=True,
        domain="[('type', 'in', ['bank', 'cash'])]",
    )
    payment_date = fields.Date(
        string='Fecha del pago',
        required=True,
        default=fields.Date.today,
    )
    memo = fields.Char(string='Notas/Referencia')

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_id = self.env.context.get('default_request_id') or self.env.context.get('active_id')
        if active_id:
            vals['request_id'] = active_id
        return vals

    def action_pay(self):
        self.ensure_one()
        req = self.request_id
        if req.state != 'approved':
            raise UserError(_('Solo se pueden pagar solicitudes aprobadas.'))
        if req.payment_id:
            raise UserError(_('Esta solicitud ya tiene un pago registrado.'))

        payment_vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': req.partner_id.id,
            'amount': req.amount,
            'currency_id': req.currency_id.id,
            'journal_id': self.journal_id.id,
            'date': self.payment_date,
            'ref': f'{req.name} - {self.memo or req.concept[:50] if req.concept else ""}',
        }
        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()

        req.write({
            'state': 'paid',
            'payment_id': payment.id,
        })
        req.message_post(
            body=_(
                '<b>Pago registrado</b><br/>Diario: %s<br/>Monto: %s %s',
                self.journal_id.name,
                req.amount,
                req.currency_id.name,
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }
