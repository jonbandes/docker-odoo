from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class PaymentRequest(models.Model):
    _name = 'payment.request'
    _description = 'Solicitud de Pago'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name desc'

    name = fields.Char(
        string='Número',
        readonly=True,
        copy=False,
        default='Nuevo',
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Proveedor',
        required=True,
        domain=[('supplier_rank', '>', 0)],
        tracking=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Solicitante',
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        tracking=True,
    )
    amount = fields.Monetary(string='Monto', required=True, tracking=True)
    currency_id = fields.Many2one(
        'res.currency',
        string='Moneda',
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    concept = fields.Text(string='Concepto', required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('sent', 'Enviada'),
        ('approved', 'Aprobada'),
        ('paid', 'Pagada'),
        ('rejected', 'Rechazada'),
    ], string='Estado', default='draft', tracking=True, index=True)

    # Tramo B
    approver_id = fields.Many2one(
        'res.users',
        string='Aprobador asignado',
        readonly=True,
        tracking=True,
    )
    approval_level_id = fields.Many2one(
        'payment.approval.level',
        string='Nivel de aprobación',
        readonly=True,
    )
    rejection_reason = fields.Text(string='Motivo de rechazo', readonly=True, tracking=True)
    approved_date = fields.Datetime(string='Fecha de aprobación', readonly=True, tracking=True)
    approved_by = fields.Many2one('res.users', string='Aprobado por', readonly=True, tracking=True)
    payment_id = fields.Many2one(
        'account.payment',
        string='Pago registrado',
        readonly=True,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('payment.request') or 'SP/NUEVO'
        return super().create(vals_list)

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('El monto debe ser mayor que cero.'))

    def _check_state(self, expected):
        self.ensure_one()
        if self.state != expected:
            raise UserError(_('Esta operación no está disponible en el estado actual.'))

    def _check_not_approver_is_requester(self):
        """Garantiza que el solicitante no pueda aprobar su propia solicitud."""
        self.ensure_one()
        if self.env.user == self.user_id and not self.env.user.has_group(
            'payment_request.group_payment_request_approver'
        ):
            raise UserError(_('El solicitante no puede aprobar su propia solicitud.'))

    def action_send(self):
        """Enviar solicitud: asigna aprobador según nivel (Tramo B)."""
        self.ensure_one()
        self._check_state('draft')
        # Asignar aprobador según monto
        approver = self.env['payment.approval.level']._get_approver_for_amount(self.amount)
        vals = {'state': 'sent'}
        if approver:
            vals['approver_id'] = approver.id
            # Crear actividad para el aprobador (Tramo B)
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=approver.id,
                note=_(
                    'Solicitud de pago %s por %s %s requiere tu aprobación.',
                    self.name,
                    self.amount,
                    self.currency_id.name,
                ),
            )
        self.write(vals)

    def action_approve(self):
        """Aprobar solicitud. Solo el aprobador asignado puede aprobar."""
        self.ensure_one()
        self._check_state('sent')
        # Verificar que el usuario sea el aprobador asignado (o no haya asignado)
        if self.approver_id and self.approver_id != self.env.user:
            raise UserError(_(
                'Solo el aprobador asignado (%s) puede aprobar esta solicitud.',
                self.approver_id.name,
            ))
        # Garantizar que el solicitante no apruebe aunque no haya nivel configurado
        if self.env.user == self.user_id and not self.env.user.has_group(
            'payment_request.group_payment_request_approver'
        ):
            raise UserError(_('El solicitante no puede aprobar su propia solicitud.'))

        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
        self.activity_feedback(['mail.mail_activity_data_todo'])

    def action_reject(self):
        """Abre el wizard de rechazo con motivo obligatorio."""
        self.ensure_one()
        self._check_state('sent')
        return {
            'name': _('Rechazar solicitud'),
            'type': 'ir.actions.act_window',
            'res_model': 'payment.request.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_pay(self):
        """Abre el wizard de pago (solo Tesorería)."""
        self.ensure_one()
        self._check_state('approved')
        if self.payment_id:
            raise UserError(_('Esta solicitud ya tiene un pago registrado.'))
        return {
            'name': _('Registrar pago'),
            'type': 'ir.actions.act_window',
            'res_model': 'payment.request.pay.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_reset_draft(self):
        self.ensure_one()
        if self.state not in ('rejected',):
            raise UserError(_('Solo se puede restablecer desde el estado rechazada.'))
        self.write({'state': 'draft', 'rejection_reason': False, 'approver_id': False})

    def action_view_payment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
        }
