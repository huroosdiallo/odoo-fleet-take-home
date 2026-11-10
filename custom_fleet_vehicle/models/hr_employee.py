from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    custom_vehicle_ids = fields.One2many(
        'custom.fleet.vehicle', 'employee_id', string='Company Vehicles',
        groups='custom_fleet_vehicle.group_custom_fleet_user',
    )
    custom_vehicle_count = fields.Integer(
        compute='_compute_custom_vehicle_count', string='Vehicle Count',
        groups='custom_fleet_vehicle.group_custom_fleet_user',
    )

    @api.depends('custom_vehicle_ids')
    def _compute_custom_vehicle_count(self):
        data = self.env['custom.fleet.vehicle']._read_group(
            [('employee_id', 'in', self.ids)], ['employee_id'], ['__count'])
        counts = {employee.id: count for employee, count in data}
        for employee in self:
            employee.custom_vehicle_count = counts.get(employee.id, 0)

    def action_open_custom_vehicles(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('custom_fleet_vehicle.action_custom_fleet_vehicle')
        action['domain'] = [('employee_id', '=', self.id)]
        action['context'] = {'default_employee_id': self.id}
        return action
