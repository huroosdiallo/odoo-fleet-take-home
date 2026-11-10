{
    'name': 'Company Vehicles (standalone)',
    'version': '19.0.1.0.0',
    'summary': "Company vehicle fleet without the Fleet app: "
               "vehicles, assigned employee, Base User / Manager groups",
    'description': """
Company vehicles assigned to employees, with Base User / Manager groups.
End-user guide (Italian): README.md. Technical notes: doc/TECNICO.md.
""",
    'category': 'Human Resources/Fleet',
    'author': 'Mahmood Diallo',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'security/custom_fleet_security.xml',
        'security/ir.model.access.csv',
        'views/custom_fleet_vehicle_views.xml',
        'views/custom_fleet_catalog_views.xml',
        'views/custom_fleet_menus.xml',
        'views/hr_employee_views.xml',
    ],
    'demo': [
        'data/custom_fleet_demo.xml',
    ],
    'application': True,
}
