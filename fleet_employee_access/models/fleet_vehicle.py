from odoo import api, fields, models
from odoo.exceptions import AccessError

DRIVER_FIELDS = ('driver_id', 'driver_employee_id', 'future_driver_id', 'future_driver_employee_id')


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    # Read-only in hr_fleet; its create/write already sync driver_id from it.
    driver_employee_id = fields.Many2one(readonly=False)
    color_ids = fields.Many2many(
        'fleet.vehicle.color', 'fleet_vehicle_color_rel', 'vehicle_id', 'color_id',
        string='Colors', copy=False,
    )

    @api.onchange('driver_employee_id')
    def _onchange_driver_employee_id(self):
        for vehicle in self:
            vehicle.driver_id = vehicle.driver_employee_id.work_contact_id

    def _is_own_vehicles_user(self):
        user = self.env.user
        return (
            not self.env.su
            and user.has_group('fleet_employee_access.group_fleet_own_vehicles')
            and not user.has_group('fleet.fleet_group_user')
        )

    def _get_own_employees(self):
        return self.env.user.sudo().employee_ids

    def _check_driver_vals(self, vals):
        employees = self._get_own_employees()
        partners = employees.work_contact_id | self.env.user.partner_id
        allowed = {
            'driver_employee_id': set(employees.ids),
            'driver_id': set(partners.ids),
            'future_driver_employee_id': set(employees.ids) | {False},
            'future_driver_id': set(partners.ids) | {False},
        }
        for field_name in DRIVER_FIELDS:
            if field_name in vals and (vals[field_name] or False) not in allowed[field_name]:
                raise AccessError(self.env._(
                    "Only a Fleet Officer or Administrator can assign a vehicle to another employee."
                ))

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if self._is_own_vehicles_user() and not res.get('driver_employee_id') and not res.get('driver_id'):
            employee = self._get_own_employees()[:1]
            if employee:
                if 'driver_employee_id' in fields:
                    res['driver_employee_id'] = employee.id
                if 'driver_id' in fields and employee.work_contact_id:
                    res['driver_id'] = employee.work_contact_id.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        if self._is_own_vehicles_user():
            employee = self._get_own_employees()[:1]
            for vals in vals_list:
                if employee and not vals.get('driver_employee_id') and not vals.get('driver_id'):
                    vals['driver_employee_id'] = employee.id
                self._check_driver_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        if self._is_own_vehicles_user():
            self._check_driver_vals(vals)
        return super().write(vals)
