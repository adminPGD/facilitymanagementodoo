# -*- coding: utf-8 -*-
"""Campus hierarchy API endpoints."""
import json

from odoo import http
from odoo.http import request

from .api_auth import api_response, api_error, api_auth_required


class FacilityCampusAPI(http.Controller):

    @http.route('/api/v1/campus', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def get_campuses(self, **kwargs):
        env = request.facility_env
        campuses = env['facility.campus'].search([])
        data = [{
            'id': c.id, 'name': c.name, 'code': c.code,
            'city': c.city, 'building_count': c.building_count,
        } for c in campuses]
        return api_response(data=data)

    @http.route('/api/v1/buildings', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def get_buildings(self, **kwargs):
        env = request.facility_env
        campus_id = kwargs.get('campus_id')
        domain = [('campus_id', '=', int(campus_id))] if campus_id else []
        buildings = env['facility.building'].search(domain)
        data = [{
            'id': b.id, 'name': b.name, 'code': b.code,
            'campus_id': b.campus_id.id, 'campus_name': b.campus_id.name,
            'building_type': b.building_type,
            'operational_status': b.operational_status,
            'total_floors': b.total_floors,
        } for b in buildings]
        return api_response(data=data)

    @http.route('/api/v1/floors', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def get_floors(self, **kwargs):
        env = request.facility_env
        building_id = kwargs.get('building_id')
        if not building_id:
            return api_error('building_id is required', status=400)
        floors = env['facility.floor'].search(
            [('building_id', '=', int(building_id))], order='floor_number')
        data = [{
            'id': f.id, 'name': f.name, 'floor_number': f.floor_number,
            'space_count': f.space_count,
        } for f in floors]
        return api_response(data=data)

    @http.route('/api/v1/spaces', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def get_spaces(self, **kwargs):
        env = request.facility_env
        domain = []
        if kwargs.get('floor_id'):
            domain.append(('floor_id', '=', int(kwargs['floor_id'])))
        if kwargs.get('building_id'):
            domain.append(('building_id', '=', int(kwargs['building_id'])))
        if kwargs.get('space_type'):
            domain.append(('space_type', '=', kwargs['space_type']))
        if kwargs.get('is_bookable'):
            domain.append(('is_bookable', '=', True))

        spaces = env['facility.space'].search(domain)
        data = [{
            'id': s.id, 'name': s.name, 'code': s.code,
            'space_type': s.space_type, 'capacity': s.capacity,
            'readiness_status': s.readiness_status,
            'operational_status': s.operational_status,
            'full_location': s.full_location,
            'building_name': s.building_id.name,
            'floor_name': s.floor_id.name,
            'is_bookable': s.is_bookable,
            'has_equipment': s.has_equipment,
            'image_url': f'/web/image/facility.space/{s.id}/image' if s.image else None,
        } for s in spaces]
        return api_response(data=data)

    @http.route('/api/v1/spaces/<int:space_id>/status', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def get_space_status(self, space_id, **kwargs):
        env = request.facility_env
        space = env['facility.space'].browse(space_id)
        if not space.exists():
            return api_error('Space not found', status=404)
        return api_response(data={
            'id': space.id, 'name': space.name,
            'readiness_status': space.readiness_status,
            'operational_status': space.operational_status,
            'asset_count': space.asset_count,
        })

    @http.route('/api/v1/request-categories', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def get_request_categories(self, **kwargs):
        env = request.facility_env
        cats = env['facility.request.category'].search([])
        data = [{
            'id': c.id, 'name': c.name, 'icon': c.icon,
            'subcategories': [{'id': sc.id, 'name': sc.name}
                              for sc in c.subcategory_ids],
        } for c in cats]
        return api_response(data=data)
