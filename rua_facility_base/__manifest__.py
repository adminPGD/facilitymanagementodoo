# -*- coding: utf-8 -*-
{
    'name': 'RUA Facility Management - Base',
    'version': '19.0.1.0.0',
    'category': 'Facility',
    'summary': 'Facility Management - Base Module',
    'description': """
        Base module for Riyadh University of Arts Facility Management System.
        
        Contains:
        - Security groups and access rights
        - SLA engine
        - Shared settings
        - Sequence definitions
        - Base mixins and utilities
    """,
    'author': 'RUA Facility Management',
    'depends': [
        'base',
        'mail',
        'portal',
    ],
    'data': [
        'security/facility_security.xml',
        'security/ir.model.access.csv',
        'data/facility_sequence_data.xml',
        'data/facility_sla_data.xml',
        'views/facility_sla_views.xml',
        'views/facility_settings_views.xml',
        'views/facility_menus.xml',
        'demo/demo_users.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
