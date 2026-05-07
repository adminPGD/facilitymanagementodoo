# -*- coding: utf-8 -*-
{
    'name': 'RUA Facility Management - Campus',
    'version': '19.0.1.0.0',
    'category': 'Facility',
    'summary': 'Facility Management - Campus and Assets',
    'description': """
        Campus hierarchy and asset management for RUA Facility Management.
        
        Models:
        - Campus → Building → Floor → Space
        - Assets linked to spaces
        - Space features and equipment
    """,
    'author': 'RUA Facility Management',
    'depends': ['rua_facility_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/facility_space_data.xml',
        'views/facility_campus_views.xml',
        'views/facility_building_views.xml',
        'views/facility_floor_views.xml',
        'views/facility_space_views.xml',
        'views/facility_asset_views.xml',
        'views/facility_campus_menus.xml',
        'demo/demo_campus.xml',
        'demo/demo_assets.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
