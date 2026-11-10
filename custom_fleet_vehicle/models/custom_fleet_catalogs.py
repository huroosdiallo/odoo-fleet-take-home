from random import randint

from odoo import api, fields, models


class CustomFleetVehicleBrand(models.Model):
    _name = 'custom.fleet.vehicle.brand'
    _description = 'Vehicle Brand'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    image_128 = fields.Image(string='Logo', max_width=128, max_height=128)
    model_ids = fields.One2many('custom.fleet.vehicle.model', 'brand_id', string='Models')
    model_count = fields.Integer(compute='_compute_model_count', string='Number of Models')

    _name_unique = models.UniqueIndex(
        '(lower(name))',
        'A brand with this name already exists.',
    )

    @api.depends('model_ids')
    def _compute_model_count(self):
        for brand in self:
            brand.model_count = len(brand.model_ids)


class CustomFleetVehicleModel(models.Model):
    _name = 'custom.fleet.vehicle.model'
    _description = 'Vehicle Model'
    _inherit = ['image.mixin']
    _order = 'brand_id, name'
    _rec_names_search = ['name', 'brand_id.name']

    name = fields.Char(required=True)
    brand_id = fields.Many2one(
        'custom.fleet.vehicle.brand',
        required=True, ondelete='restrict', index=True,
    )
    active = fields.Boolean(default=True)

    _brand_name_unique = models.UniqueIndex(
        '(brand_id, lower(name))',
        'This brand already has a model with this name.',
    )


class CustomFleetVehicleColor(models.Model):
    _name = 'custom.fleet.vehicle.color'
    _description = 'Vehicle Color'
    _order = 'name'

    name = fields.Char(required=True)
    color = fields.Integer(string='Color Index', default=lambda self: randint(1, 11))
    active = fields.Boolean(default=True)

    _name_unique = models.UniqueIndex(
        '(lower(name))',
        'A color with this name already exists.',
    )
