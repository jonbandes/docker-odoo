from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PaymentRequestRejectWizard(models.TransientModel):
    _name = 'payment.request.reject.wizard'
    _description = 'Asistente de Rechazo de Solicitud de Pago'

    request_id = fields.Many2one(
        'payment.request',
        string='Solicitud',
        required=True,
        readonly=True,
    )
    reason = fields.Text(string='Motivo de rechazo', required=True)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_id = self.env.context.get('default_request_id') or self.env.context.get('active_id')
        if active_id:
            vals['request_id'] = active_id
        return vals

    def action_reject(self):
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            raise UserError(_('El motivo de rechazo es obligatorio.'))
        request = self.request_id
        request.write({
            'state': 'rejected',
            'rejection_reason': self.reason.strip(),
        })
        request.message_post(
            body=_('<b>Solicitud rechazada</b><br/>Motivo: %s', self.reason.strip()),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        request.activity_feedback(['mail.mail_activity_data_todo'])
        return {'type': 'ir.actions.act_window_close'}
