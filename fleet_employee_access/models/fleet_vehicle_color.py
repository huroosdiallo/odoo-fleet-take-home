from random import randint

from odoo import fields, models


class FleetVehicleColor(models.Model):
    _name = 'fleet.vehicle.color'
    _description = 'Vehicle Color'
    _order = 'sequence, name'

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer(string='Tag Color', default=_default_color)
    active = fields.Boolean(default=True)
