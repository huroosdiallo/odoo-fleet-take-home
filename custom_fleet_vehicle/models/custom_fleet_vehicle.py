import re

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

# Loose on purpose: foreign and vintage plates must pass too.
PLATE_PATTERN = re.compile(r'[A-Z0-9-]{2,12}')


class CustomFleetVehicle(models.Model):
    _name = 'custom.fleet.vehicle'
    _description = 'Company Vehicle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'license_plate'
    _rec_names_search = ['name', 'license_plate', 'brand_id.name', 'model_id.name']

    name = fields.Char(compute='_compute_name', store=True)
    license_plate = fields.Char(required=True, tracking=True)
    brand_id = fields.Many2one(
        'custom.fleet.vehicle.brand',
        required=True, ondelete='restrict', tracking=True, index=True,
    )
    model_id = fields.Many2one(
        'custom.fleet.vehicle.model',
        required=True, ondelete='restrict', tracking=True, index=True,
        domain="[('brand_id', '=?', brand_id)]",
    )
    image_128 = fields.Image(related='model_id.image_128', readonly=True)
    year = fields.Integer(string='Registration Year', tracking=True)
    color_ids = fields.Many2many(
        'custom.fleet.vehicle.color', 'custom_fleet_vehicle_color_rel',
        'vehicle_id', 'color_id', string='Colors',
    )
    employee_id = fields.Many2one(
        'hr.employee', tracking=True, index=True,
        default=lambda self: self._default_employee(),
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    user_id = fields.Many2one(
        'res.users', related='employee_id.user_id',
        store=True, index=True,
        help="User of the assigned employee: decides who can see the vehicle.",
    )
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )
    notes = fields.Text()
    active = fields.Boolean(default=True, tracking=True)

    _license_plate_unique = models.Constraint(
        'UNIQUE(license_plate)',
        'A vehicle with this license plate already exists.',
    )

    @api.depends('brand_id.name', 'model_id.name', 'license_plate')
    def _compute_name(self):
        for car in self:
            car.name = ' '.join(filter(None, [car.brand_id.name, car.model_id.name])) + (
                f' ({car.license_plate})' if car.license_plate else '')

    @api.constrains('license_plate')
    def _check_license_plate_format(self):
        for car in self:
            if not PLATE_PATTERN.fullmatch(car.license_plate or ''):
                raise ValidationError(self.env._(
                    "The license plate %(plate)s is not valid: use 2 to 12 letters, digits or dashes.",
                    plate=car.license_plate,
                ))

    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.model_id and self.model_id.brand_id != self.brand_id:
            self.model_id = False

    @api.onchange('model_id')
    def _onchange_model_id(self):
        if self.model_id:
            self.brand_id = self.model_id.brand_id

    @api.constrains('brand_id', 'model_id')
    def _check_model_brand(self):
        for car in self:
            if car.model_id.brand_id != car.brand_id:
                raise ValidationError(self.env._(
                    "The model %(model)s is not a %(brand)s model.",
                    model=car.model_id.name, brand=car.brand_id.name,
                ))

    def _is_restricted_user(self):
        user = self.env.user
        return (
            not self.env.su
            and user.has_group('custom_fleet_vehicle.group_custom_fleet_user')
            and not user.has_group('custom_fleet_vehicle.group_custom_fleet_manager')
        )

    @api.model
    def _default_employee(self):
        return self.env.user.employee_id if self._is_restricted_user() else False

    def _check_assigned_to_self(self):
        # Write rules are checked on the record before the change: check the result too.
        for car in self.sudo():
            if car.user_id != self.env.user:
                raise AccessError(self.env._("Only a Fleet Manager can assign a vehicle to another employee."))

    @staticmethod
    def _normalize_plate(plate):
        return ''.join(plate.split()).upper()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('license_plate'):
                vals['license_plate'] = self._normalize_plate(vals['license_plate'])
        cars = super().create(vals_list)
        if cars._is_restricted_user():
            cars._check_assigned_to_self()
        return cars

    def write(self, vals):
        if vals.get('license_plate'):
            vals['license_plate'] = self._normalize_plate(vals['license_plate'])
        res = super().write(vals)
        if 'employee_id' in vals and self._is_restricted_user():
            self._check_assigned_to_self()
        return res
