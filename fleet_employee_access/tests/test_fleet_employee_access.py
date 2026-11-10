from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestFleetEmployeeAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_user = new_test_user(
            cls.env, login='fea_base', name='Base Driver',
            groups='base.group_user,fleet_employee_access.group_fleet_own_vehicles',
        )
        cls.other_user = new_test_user(
            cls.env, login='fea_other', name='Other Driver',
            groups='base.group_user,fleet_employee_access.group_fleet_own_vehicles',
        )
        cls.officer = new_test_user(
            cls.env, login='fea_officer', name='Fleet Officer', groups='base.group_user,fleet.fleet_group_user',
        )
        cls.manager = new_test_user(
            cls.env, login='fea_manager', name='Fleet Manager', groups='base.group_user,fleet.fleet_group_manager',
        )
        Employee = cls.env['hr.employee']
        cls.base_employee = Employee.create({'name': 'Base Driver', 'user_id': cls.base_user.id})
        cls.other_employee = Employee.create({'name': 'Other Driver', 'user_id': cls.other_user.id})
        cls.no_user_employee = Employee.create({'name': 'Employee Without User'})

        brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'Test Brand'})
        cls.model = cls.env['fleet.vehicle.model'].create({'name': 'Test Model', 'brand_id': brand.id})
        cls.red = cls.env['fleet.vehicle.color'].create({'name': 'Test Red'})
        cls.black = cls.env['fleet.vehicle.color'].create({'name': 'Test Black'})

        Vehicle = cls.env['fleet.vehicle']
        cls.own_vehicle = Vehicle.create({
            'model_id': cls.model.id, 'license_plate': 'TEST-OWN', 'driver_employee_id': cls.base_employee.id,
        })
        cls.other_vehicle = Vehicle.create({
            'model_id': cls.model.id, 'license_plate': 'TEST-OTHER', 'driver_employee_id': cls.other_employee.id,
        })
        cls.free_vehicle = Vehicle.create({'model_id': cls.model.id, 'license_plate': 'TEST-FREE'})
        cls.test_vehicles = cls.own_vehicle | cls.other_vehicle | cls.free_vehicle

    def _visible(self, user):
        return self.env['fleet.vehicle'].with_user(user).search([('id', 'in', self.test_vehicles.ids)])

    def test_group_hierarchy(self):
        own_group = self.env.ref('fleet_employee_access.group_fleet_own_vehicles')
        self.assertIn(own_group, self.env.ref('fleet.fleet_group_user').all_implied_ids)
        self.assertTrue(self.manager.has_group('fleet_employee_access.group_fleet_own_vehicles'))
        self.assertFalse(self.base_user.has_group('fleet.fleet_group_user'))

    def test_employee_assignment_syncs_driver(self):
        self.assertEqual(self.own_vehicle.driver_id, self.base_employee.work_contact_id)
        self.own_vehicle.driver_employee_id = self.other_employee
        self.assertEqual(self.own_vehicle.driver_id, self.other_employee.work_contact_id)

    def test_base_user_sees_only_own_vehicles(self):
        self.assertEqual(self._visible(self.base_user), self.own_vehicle)
        self.assertEqual(self._visible(self.other_user), self.other_vehicle)

    def test_base_user_cannot_read_other_vehicle(self):
        with self.assertRaises(AccessError):
            self.other_vehicle.with_user(self.base_user).read(['license_plate'])

    def test_officer_and_manager_see_all(self):
        self.assertEqual(self._visible(self.officer), self.test_vehicles)
        self.assertEqual(self._visible(self.manager), self.test_vehicles)

    def test_user_without_employee_sees_nothing(self):
        lonely = new_test_user(
            self.env, login='fea_lonely', groups='base.group_user,fleet_employee_access.group_fleet_own_vehicles',
        )
        self.assertFalse(self._visible(lonely))

    def test_my_vehicles_filter(self):
        action = self.env.ref('fleet_employee_access.fleet_vehicle_my_action')
        self.assertEqual(action.context, "{'search_default_my_vehicles': 1}")
        domain = [('driver_employee_id.user_id', '=', self.manager.id), ('id', 'in', self.test_vehicles.ids)]
        self.assertFalse(self.env['fleet.vehicle'].with_user(self.manager).search(domain))
        self.other_vehicle.driver_employee_id = self.env['hr.employee'].create(
            {'name': 'Fleet Manager', 'user_id': self.manager.id})
        self.assertEqual(self.env['fleet.vehicle'].with_user(self.manager).search(domain), self.other_vehicle)

    def test_base_user_creates_own_vehicle(self):
        Vehicle = self.env['fleet.vehicle'].with_user(self.base_user)
        defaults = Vehicle.default_get(['driver_employee_id', 'driver_id'])
        self.assertEqual(defaults['driver_employee_id'], self.base_employee.id)
        vehicle = Vehicle.create({'model_id': self.model.id, 'license_plate': 'TEST-NEW'})
        self.assertEqual(vehicle.driver_employee_id, self.base_employee)
        vehicle.write({'license_plate': 'TEST-NEW2', 'color_ids': [Command.set((self.red | self.black).ids)]})
        self.assertEqual(vehicle.color_ids, self.red | self.black)

    def test_base_user_cannot_assign_to_others(self):
        Vehicle = self.env['fleet.vehicle'].with_user(self.base_user)
        with self.assertRaises(AccessError):
            Vehicle.create({
                'model_id': self.model.id, 'license_plate': 'TEST-X', 'driver_employee_id': self.other_employee.id,
            })
        own = self.own_vehicle.with_user(self.base_user)
        for vals in (
            {'driver_employee_id': self.other_employee.id},
            {'driver_employee_id': False},
            {'driver_id': self.other_employee.work_contact_id.id},
            {'future_driver_employee_id': self.other_employee.id},
        ):
            with self.subTest(vals=vals), self.assertRaises(AccessError):
                own.write(vals)
        self.assertEqual(self.own_vehicle.driver_employee_id, self.base_employee)

    def test_base_user_cannot_edit_or_take_other_vehicles(self):
        with self.assertRaises(AccessError):
            self.other_vehicle.with_user(self.base_user).write({'license_plate': 'HACK'})
        with self.assertRaises(AccessError):
            self.free_vehicle.with_user(self.base_user).write({'driver_employee_id': self.base_employee.id})

    def test_base_user_cannot_delete(self):
        with self.assertRaises(AccessError):
            self.own_vehicle.with_user(self.base_user).unlink()

    def test_manager_reassigns_and_deletes(self):
        self.own_vehicle.with_user(self.officer).driver_employee_id = self.other_employee
        self.assertEqual(self.own_vehicle.driver_id, self.other_employee.work_contact_id)
        self.own_vehicle.with_user(self.manager).driver_employee_id = self.base_employee
        self.assertEqual(self.own_vehicle.driver_id, self.base_employee.work_contact_id)
        self.assertEqual(self._visible(self.manager), self.test_vehicles)
        self.free_vehicle.with_user(self.officer).unlink()
        self.assertFalse(self.free_vehicle.exists())

    def test_base_user_odometer_and_history_own_only(self):
        self.own_vehicle.with_user(self.base_user).odometer = 1200
        Odometer = self.env['fleet.vehicle.odometer']
        Odometer.create({'vehicle_id': self.other_vehicle.id, 'value': 500})
        visible = Odometer.with_user(self.base_user).search([('vehicle_id', 'in', self.test_vehicles.ids)])
        self.assertEqual(visible.vehicle_id, self.own_vehicle)
        logs = self.env['fleet.vehicle.assignation.log'].with_user(self.base_user).search(
            [('vehicle_id', 'in', self.test_vehicles.ids)])
        self.assertEqual(logs.vehicle_id, self.own_vehicle)
        with self.assertRaises(AccessError):
            Odometer.with_user(self.base_user).create({'vehicle_id': self.other_vehicle.id, 'value': 10})

    def test_colors_catalog_rights(self):
        Color = self.env['fleet.vehicle.color']
        self.assertTrue(Color.with_user(self.base_user).search([('id', '=', self.red.id)]))
        with self.assertRaises(AccessError):
            Color.with_user(self.base_user).create({'name': 'Pink'})
        self.assertTrue(Color.with_user(self.officer).create({'name': 'Pink'}))
        self.assertTrue(Color.with_user(self.manager).create({'name': 'Purple'}))

    def test_brand_and_model_catalog_rights(self):
        Brand = self.env['fleet.vehicle.model.brand']
        Model = self.env['fleet.vehicle.model']
        for user in (self.officer, self.manager):
            with self.subTest(user=user.login):
                brand = Brand.with_user(user).create({'name': 'Brand %s' % user.login})
                model = Model.with_user(user).create({'name': 'Model %s' % user.login, 'brand_id': brand.id})
                brand.name += ' bis'
                model.name += ' bis'
                vehicle = self.env['fleet.vehicle'].with_user(user).create({
                    'model_id': model.id, 'driver_employee_id': self.other_employee.id,
                })
                self.assertEqual(vehicle.brand_id, brand)
        base_brand = Brand.with_user(self.base_user)
        self.assertTrue(base_brand.search([('id', '=', self.model.brand_id.id)]))
        with self.assertRaises(AccessError):
            base_brand.create({'name': 'Base Brand'})
        with self.assertRaises(AccessError):
            Model.with_user(self.base_user).create({'name': 'Base Model', 'brand_id': self.model.brand_id.id})
        with self.assertRaises(AccessError):
            self.model.with_user(self.base_user).write({'name': 'Renamed'})

    def test_model_field_create_option_per_role(self):
        expected = {self.officer: False, self.manager: False, self.base_user: True}
        for user, no_create in expected.items():
            with self.subTest(user=user.login):
                arch = self.env['fleet.vehicle'].with_user(user).get_views([(False, 'form')])['views']['form']['arch']
                nodes = etree.fromstring(arch).xpath("//field[@name='model_id']")
                self.assertEqual(len(nodes), 1)
                self.assertEqual("'no_create': True" in (nodes[0].get('options') or ''), no_create)

    def test_views_load_for_each_role(self):
        for user in (self.base_user, self.officer, self.manager):
            with self.subTest(user=user.login):
                views = self.env['fleet.vehicle'].with_user(user).get_views(
                    [(False, 'form'), (False, 'list'), (False, 'kanban'), (False, 'search')])
                self.assertIn('color_ids', views['models']['fleet.vehicle']['fields'])
                vehicle = self.own_vehicle.with_user(self.base_user)
                self.assertTrue(vehicle.display_name)

    def test_menus_for_base_user(self):
        visible = self.env['ir.ui.menu'].with_user(self.base_user)._visible_menu_ids()
        self.assertIn(self.env.ref('fleet_employee_access.fleet_vehicle_my_menu').id, visible)
        self.assertIn(self.env.ref('fleet.menu_root').id, visible)
        self.assertNotIn(self.env.ref('fleet.fleet_vehicle_menu').id, visible)
        self.assertNotIn(self.env.ref('fleet.fleet_configuration').id, visible)
        self.assertNotIn(self.env.ref('fleet_employee_access.fleet_vehicle_color_menu').id, visible)
        manager_visible = self.env['ir.ui.menu'].with_user(self.manager)._visible_menu_ids()
        self.assertIn(self.env.ref('fleet_employee_access.fleet_vehicle_color_menu').id, manager_visible)
