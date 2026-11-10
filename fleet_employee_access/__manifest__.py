{
    'name': 'Fleet - Employee Based Access',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Fleet',
    'summary': 'Base users see and register only the vehicles assigned to their own employee',
    'description': "Extends Fleet and Fleet History (hr_fleet). User guide (Italian): README.md.",
    'author': 'Mahmood Diallo',
    'license': 'LGPL-3',
    'depends': ['fleet', 'hr', 'hr_fleet'],
    'data': [
        'security/fleet_employee_access_security.xml',
        'security/ir.model.access.csv',
        'data/fleet_vehicle_color_data.xml',
        'views/fleet_vehicle_color_views.xml',
        'views/fleet_vehicle_views.xml',
    ],
    'demo': [
        'demo/fleet_employee_access_demo.xml',
    ],
    'installable': True,
    'application': False,
}
