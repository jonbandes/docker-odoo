from odoo import fields, models


class FleetInspectionPoint(models.Model):
    _name = 'fleet.inspection.point'
    _description = 'Punto de inspección'
    _order = 'sequence, id'

    inspection_id = fields.Many2one(
        'fleet.inspection',
        string='Inspección',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Punto', required=True)
    result = fields.Selection([
        ('pass', 'Pasa'),
        ('fail', 'Falla'),
        ('na', 'N/A'),
    ], string='Resultado', default='na', required=True)
    notes = fields.Char(string='Notas')
