# -*- coding: utf-8 -*-
{
    'name': 'RUA Facility Management - Operations',
    'version': '19.0.1.0.0',
    'category': 'Facility',
    'summary': 'Facility Management - Requests and Work Orders',
    'description': """
        Core operations module for RUA Facility Management.
        
        Contains:
        - Unified request model (maintenance, observation, service, event, safety)
        - Work order management with checklists
        - Rating and evaluation
        - Preventive maintenance planning
        - SLA deadline enforcement
        - Cron jobs for SLA and preventive maintenance
    """,
    'author': 'RUA Facility Management',
    'depends': [
        'rua_facility_base',
        'rua_facility_campus',
        'maintenance',
        'product',
    ],
    'data': [
        'security/facility_operations_security.xml',
        'security/ir.model.access.csv',
        'data/facility_request_category_data.xml',
        'views/facility_dashboard_views.xml',
        'views/facility_request_views.xml',
        'views/facility_work_order_views.xml',
        'views/facility_rating_views.xml',
        'views/facility_operations_menus.xml',
        'demo/demo_requests.xml',
        'demo/demo_work_orders.xml',
        'demo/demo_ratings.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'rua_facility_operations/static/src/dashboard/facility_dashboard.js',
            'rua_facility_operations/static/src/dashboard/facility_dashboard.css',
            'rua_facility_operations/static/src/dashboard/facility_dashboard.xml',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}
