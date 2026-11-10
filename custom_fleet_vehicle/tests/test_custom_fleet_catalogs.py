from psycopg2 import IntegrityError

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import Form, TransactionCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestCustomFleetCatalogs(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = 'base.group_user,custom_fleet_vehicle.group_custom_fleet_'
        cls.user_base = new_test_user(cls.env, login='cat_base', groups=groups + 'user')
        cls.user_manager = new_test_user(cls.env, login='cat_manager', groups=groups + 'manager')
        cls.emp_base = cls.env['hr.employee'].create({'name': 'Cat Base', 'user_id': cls.user_base.id})
        Brand = cls.env['custom.fleet.vehicle.brand']
        Model = cls.env['custom.fleet.vehicle.model']
        cls.brand_a = Brand.create({'name': 'Alfamarca'})
        cls.brand_b = Brand.create({'name': 'Betamarca'})
        cls.model_a = Model.create({'name': 'Uno', 'brand_id': cls.brand_a.id})
        cls.model_b = Model.create({'name': 'Due', 'brand_id': cls.brand_b.id})
        Color = cls.env['custom.fleet.vehicle.color']
        cls.color = Color.create({'name': 'Verdolino'})
        cls.color_2 = Color.create({'name': 'Lillino'})

    def _create_dup(self, model, vals):
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env[model].create(vals)

    def test_brand_unique_case_insensitive(self):
        self._create_dup('custom.fleet.vehicle.brand', {'name': 'ALFAMARCA'})

    def test_model_unique_per_brand(self):
        self._create_dup('custom.fleet.vehicle.model', {'name': 'uno', 'brand_id': self.brand_a.id})
        other = self.env['custom.fleet.vehicle.model'].create({'name': 'Uno', 'brand_id': self.brand_b.id})
        self.assertEqual(other.brand_id, self.brand_b, "the same model name is allowed for another brand")

    def test_color_unique_case_insensitive(self):
        self._create_dup('custom.fleet.vehicle.color', {'name': 'verdolino'})

    def test_model_must_match_brand(self):
        Car = self.env['custom.fleet.vehicle']
        with self.assertRaises(ValidationError):
            Car.create({'license_plate': 'CAT001', 'brand_id': self.brand_a.id, 'model_id': self.model_b.id})
        car = Car.create({'license_plate': 'CAT002', 'brand_id': self.brand_a.id, 'model_id': self.model_a.id})
        with self.assertRaises(ValidationError):
            car.write({'brand_id': self.brand_b.id})

    def test_form_model_first_fills_brand(self):
        form = Form(self.env['custom.fleet.vehicle'].with_user(self.user_manager))
        form.license_plate = 'CAT003'
        form.model_id = self.model_b
        self.assertEqual(form.brand_id, self.brand_b)
        form.brand_id = self.brand_a
        self.assertFalse(form.model_id, "a model of another brand is cleared")
        form.model_id = self.model_a
        form.color_ids.add(self.color)
        form.color_ids.add(self.color_2)
        car = form.save()
        self.assertEqual(car.name, 'Alfamarca Uno (CAT003)')
        self.assertEqual(car.color_ids, self.color | self.color_2)

    def test_multiple_colors_and_color_search(self):
        Car = self.env['custom.fleet.vehicle']
        two = Car.create({'license_plate': 'CAT006', 'brand_id': self.brand_a.id, 'model_id': self.model_a.id,
                          'color_ids': [Command.set((self.color | self.color_2).ids)]})
        none = Car.create({'license_plate': 'CAT007', 'brand_id': self.brand_a.id, 'model_id': self.model_a.id})
        self.assertIn(two, Car.search([('color_ids', 'ilike', 'Lillino')]))
        self.assertNotIn(none, Car.search([('color_ids', 'ilike', 'Lillino')]))
        self.assertIn(none, Car.search([('color_ids', '=', False)]))
        self.color_2.with_user(self.user_manager).unlink()
        self.assertEqual(two.color_ids, self.color, "deleting a color only removes it from the vehicles")

    def test_manager_creates_color_on_the_fly(self):
        car = self.env['custom.fleet.vehicle'].with_user(self.user_manager).create({
            'license_plate': 'CAT008', 'brand_id': self.brand_a.id, 'model_id': self.model_a.id,
            'color_ids': [Command.create({'name': 'Perlato'})],
        })
        self.assertEqual(car.color_ids.name, 'Perlato')

    def test_search_vehicle_by_brand_and_model(self):
        car = self.env['custom.fleet.vehicle'].create(
            {'license_plate': 'CAT004', 'brand_id': self.brand_b.id, 'model_id': self.model_b.id})
        Car = self.env['custom.fleet.vehicle']
        self.assertIn(car, Car.search([('brand_id', 'ilike', 'Betamarca')]))
        self.assertIn(car, Car.search([('display_name', 'ilike', 'Due')]))

    def test_base_user_reads_but_cannot_edit_catalogs(self):
        for model, record in (
            ('custom.fleet.vehicle.brand', self.brand_a),
            ('custom.fleet.vehicle.model', self.model_a),
            ('custom.fleet.vehicle.color', self.color),
        ):
            Catalog = self.env[model].with_user(self.user_base)
            self.assertTrue(Catalog.name_search(record.name), model)
            vals = {'name': 'Nuovo'}
            if model == 'custom.fleet.vehicle.model':
                vals['brand_id'] = self.brand_a.id
            with self.assertRaises(AccessError):
                Catalog.create(vals)
            with self.assertRaises(AccessError):
                record.with_user(self.user_base).write({'name': 'Cambiato'})
            with self.assertRaises(AccessError):
                record.with_user(self.user_base).unlink()

    def test_base_user_picks_catalog_values(self):
        car = self.env['custom.fleet.vehicle'].with_user(self.user_base).create({
            'license_plate': 'CAT005', 'brand_id': self.brand_a.id,
            'model_id': self.model_a.id, 'color_ids': [Command.set((self.color | self.color_2).ids)],
        })
        self.assertEqual(car.employee_id, self.emp_base)
        self.assertEqual(car.color_ids, self.color | self.color_2)
        car.write({'color_ids': [Command.unlink(self.color_2.id)]})
        self.assertEqual(car.color_ids, self.color)
        with self.assertRaises(AccessError):
            car.write({'color_ids': [Command.create({'name': 'Colore inventato'})]})

    def test_manager_manages_catalogs(self):
        brand = self.env['custom.fleet.vehicle.brand'].with_user(self.user_manager).create({'name': 'Gammamarca'})
        model = self.env['custom.fleet.vehicle.model'].with_user(self.user_manager).create(
            {'name': 'Tre', 'brand_id': brand.id})
        self.env['custom.fleet.vehicle.color'].with_user(self.user_manager).create({'name': 'Ocra'})
        brand.write({'name': 'Gamma'})
        self.assertEqual(brand.model_count, 1)
        model.unlink()
        brand.unlink()
        self.assertFalse(brand.exists())

    def test_vehicle_image_follows_model(self):
        png = (b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')
        self.model_a.image_1920 = png
        car = self.env['custom.fleet.vehicle'].create(
            {'license_plate': 'CAT009', 'brand_id': self.brand_a.id, 'model_id': self.model_a.id})
        self.assertTrue(car.image_128)
        self.assertEqual(car.image_128, self.model_a.image_128)
        car.write({'brand_id': self.brand_b.id, 'model_id': self.model_b.id})
        self.assertFalse(car.image_128, "the image changes with the model")

    def test_all_views_load(self):
        Car = self.env['custom.fleet.vehicle']
        for view_type in ('list', 'kanban', 'form', 'search', 'pivot', 'graph', 'activity'):
            for user in (self.user_base, self.user_manager):
                self.assertTrue(Car.with_user(user).get_view(view_type=view_type)['arch'], view_type)
