from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestCustomFleetSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        user_groups = 'base.group_user,custom_fleet_vehicle.group_custom_fleet_user'
        manager_groups = 'base.group_user,custom_fleet_vehicle.group_custom_fleet_manager'
        cls.user_base = new_test_user(cls.env, login='c_base', groups=user_groups)
        cls.user_other = new_test_user(cls.env, login='c_other', groups=user_groups)
        cls.user_manager = new_test_user(cls.env, login='c_manager', groups=manager_groups)
        Employee = cls.env['hr.employee']
        cls.emp_base = Employee.create({'name': 'Base', 'user_id': cls.user_base.id})
        cls.emp_other = Employee.create({'name': 'Altro', 'user_id': cls.user_other.id})
        cls.brand = cls.env['custom.fleet.vehicle.brand'].create({'name': 'Testmarca'})
        cls.model = cls.env['custom.fleet.vehicle.model'].create({'name': 'Panda', 'brand_id': cls.brand.id})
        car_vals = {'brand_id': cls.brand.id, 'model_id': cls.model.id}
        Car = cls.env['custom.fleet.vehicle']
        cls.car_base = Car.create({**car_vals, 'license_plate': 'CT001', 'employee_id': cls.emp_base.id})
        cls.car_other = Car.create({**car_vals, 'license_plate': 'CT002', 'employee_id': cls.emp_other.id})
        cls.car_free = Car.create({**car_vals, 'license_plate': 'CT003'})
        cls.car_vals = car_vals

    def _plates(self, user):
        return set(self.env['custom.fleet.vehicle'].with_user(user).search(
            [('license_plate', 'like', 'CT00')]).mapped('license_plate'))

    def test_user_follows_employee(self):
        self.assertEqual(self.car_base.user_id, self.user_base)
        self.assertEqual(self.car_base.name, 'Testmarca Panda (CT001)')

    def test_base_sees_only_own(self):
        self.assertEqual(self._plates(self.user_base), {'CT001'})
        with self.assertRaises(AccessError):
            self.car_other.with_user(self.user_base).read(['license_plate'])

    def test_manager_sees_all(self):
        self.assertEqual(self._plates(self.user_manager), {'CT001', 'CT002', 'CT003'})

    def test_my_vehicles_filter(self):
        Car = self.env['custom.fleet.vehicle'].with_user(self.user_manager)
        self.assertFalse(Car.search([('user_id', '=', self.user_manager.id), ('license_plate', 'like', 'CT00')]))

    def test_base_form_reads_employee_name(self):
        data = self.car_base.with_user(self.user_base).web_read({'employee_id': {'fields': {'display_name': {}}}})
        self.assertEqual(data[0]['employee_id']['display_name'], 'Base')

    def test_base_write_own_not_others(self):
        self.car_base.with_user(self.user_base).write({'year': 2020})
        with self.assertRaises(AccessError):
            self.car_other.with_user(self.user_base).write({'year': 2021})

    def test_base_create_for_self_only(self):
        Car = self.env['custom.fleet.vehicle'].with_user(self.user_base)
        car = Car.create({**self.car_vals, 'license_plate': 'CT010'})
        self.assertEqual(car.employee_id, self.emp_base, "the proposed employee is the user's own")
        with self.assertRaises(AccessError):
            Car.create({**self.car_vals, 'license_plate': 'CT011', 'employee_id': self.emp_other.id})

    def test_base_cannot_reassign(self):
        for employee in (self.emp_other, False):
            with self.assertRaises(AccessError), self.cr.savepoint():
                self.car_base.with_user(self.user_base).write({'employee_id': employee and employee.id})
            self.car_base.invalidate_recordset()
            self.assertEqual(self.car_base.employee_id, self.emp_base)

    def test_base_cannot_take_free_vehicle(self):
        with self.assertRaises(AccessError):
            self.car_free.with_user(self.user_base).write({'employee_id': self.emp_base.id})

    def test_manager_can_reassign(self):
        self.car_base.with_user(self.user_manager).write({'employee_id': self.emp_other.id})
        self.assertEqual(self.car_base.user_id, self.user_other)

    def test_base_cannot_unlink(self):
        with self.assertRaises(AccessError):
            self.car_base.with_user(self.user_base).unlink()

    def test_manager_unlinks(self):
        self.car_other.with_user(self.user_manager).unlink()
        self.assertFalse(self.car_other.exists())

    def test_plate_unique_and_normalized(self):
        car = self.env['custom.fleet.vehicle'].create({**self.car_vals, 'license_plate': ' ct 020 '})
        self.assertEqual(car.license_plate, 'CT020')
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env['custom.fleet.vehicle'].create({**self.car_vals, 'license_plate': 'CT020'})

    def test_plate_format(self):
        Car = self.env['custom.fleet.vehicle']
        for plate in ('X', 'AB#123', 'ABCDEFGHIJKLM'):
            with self.assertRaises(ValidationError), self.cr.savepoint():
                Car.create({**self.car_vals, 'license_plate': plate})
        for plate in ('ab-123-cd', 'M 12345', 'ZH123456'):
            self.assertTrue(Car.create({**self.car_vals, 'license_plate': plate}))

    def test_employee_vehicle_count(self):
        self.assertEqual(self.emp_base.custom_vehicle_count, 1)
        self.assertEqual(self.emp_base.custom_vehicle_ids, self.car_base)
        self.assertEqual(self.emp_other.with_user(self.user_base).custom_vehicle_count, 0)
        action = self.emp_base.action_open_custom_vehicles()
        self.assertEqual(self.env['custom.fleet.vehicle'].search(action['domain']), self.car_base)
        self.assertEqual(action['context']['default_employee_id'], self.emp_base.id)

    def test_activities_and_tracking(self):
        car = self.car_base.with_user(self.user_base)
        car.activity_schedule('mail.mail_activity_data_todo', summary='Service', user_id=self.user_base.id)
        self.assertEqual(len(car.activity_ids), 1)
        car = self.env['custom.fleet.vehicle'].create(
            {**self.car_vals, 'license_plate': 'CT030', 'employee_id': self.emp_base.id})
        self.cr.flush()
        car.with_user(self.user_manager).write({'employee_id': self.emp_other.id})
        self.cr.flush()
        tracked = car.message_ids.tracking_value_ids.field_id.mapped('name')
        self.assertIn('employee_id', tracked)
