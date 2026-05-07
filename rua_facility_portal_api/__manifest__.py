# -*- coding: utf-8 -*-
{
    'name': 'RUA Facility Management - Portal API',
    'version': '19.0.1.0.0',
    'category': 'Facility',
    'summary': 'Facility Management - Portal REST API',
    'description': """
        REST API layer for the Next.js Facility Management Portal.
        
        Features:
        - JWT token authentication
        - JSON-only responses (no HTML redirects)
        - CORS support
        - Paginated list endpoints
        - File upload/download
    """,
    'author': 'RUA Facility Management',
    'depends': [
        'rua_facility_base',
        'rua_facility_campus',
        'rua_facility_operations',
    ],
    'data': [],
    'external_dependencies': {
        'python': ['PyJWT'],
    },
    'installable': True,
    'license': 'LGPL-3',
}
