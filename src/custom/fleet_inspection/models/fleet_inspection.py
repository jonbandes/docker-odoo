# NOTA: este archivo es la versión ORIGINAL para Odoo 16.
# Usa attrs y states que están deprecated en Odoo 17.
# La migración a 17 se hace en la versión 17.0.1.0.0.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FleetInspection(models.Model):
    _name = 'fleet.inspection'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Referencia',
        required=True,
        copy=False,
        default=lambda self: _('Nueva inspección'),
        tracking=True,
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Vehículo',
        required=True,
        tracking=True,
    )
    vehicle_type = fields.Selection([
        ('moto', 'Moto'),
        ('car', 'Carro'),
        ('truck', 'Camión'),
        ('other', 'Otro'),
    ], string='Tipo de vehículo', required=True, tracking=True)
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.today,
        tracking=True,
    )
    inspector_id = fields.Many2one(
        'res.users',
        string='Inspector',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_progress', 'En curso'),
        ('approved', 'Aprobada'),
        ('rejected', 'Rechazada'),
    ], string='Estado', default='draft', tracking=True)
    notes = fields.Text(string='Observaciones')
    rejection_reason = fields.Text(string='Motivo de rechazo')
    inspection_line_ids = fields.One2many(
        'fleet.inspection.point',
        'inspection_id',
        string='Puntos de inspección',
    )

    def action_start(self):
        self.ensure_one()
        self.write({'state': 'in_progress'})

    def action_approve(self):
        self.ensure_one()
        if any(line.result == 'fail' for line in self.inspection_line_ids):
            raise ValidationError(
                _('Existen puntos con resultado fallido. Corrija antes de aprobar.')
            )
        self.write({'state': 'approved'})

    def action_reject(self):
        self.ensure_one()
        if not self.rejection_reason:
            raise ValidationError(_('Debe indicar el motivo de rechazo.'))
        self.write({'state': 'rejected'})

    def action_reset_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})
