# -*- coding: utf-8 -*-
"""
Manager, Technician, and Contractor API endpoints.
Provides role-specific views for work orders, contracts, and extended dashboard.

Security:
- Manager endpoints verify user has MANAGER_ROLES facility_role
- Technician endpoints verify work order is assigned to current user
- Contractor endpoints verify work order contractor matches current user partner
"""
import json
from odoo import http
from odoo.http import request

from .api_auth import (
    api_response, api_error, api_auth_required,
    MANAGER_ROLES, _get_portal_role,
)


class FacilityManagerAPI(http.Controller):
    """Endpoints for facility managers — see all requests and work orders."""

    def _serialize_work_order(self, wo):
        return {
            'id': wo.id,
            'name': wo.name,
            'title': wo.title,
            'description': wo.description or '',
            'state': wo.state,
            'priority': wo.priority,
            'risk_level': wo.risk_level,
            'source_request_id': wo.source_request_id.id if wo.source_request_id else None,
            'source_request_name': wo.source_request_id.name if wo.source_request_id else None,
            'source_type': wo.source_type,
            'location': {
                'campus': {'id': wo.campus_id.id, 'name': wo.campus_id.name} if wo.campus_id else None,
                'building': {'id': wo.building_id.id, 'name': wo.building_id.name} if wo.building_id else None,
                'floor': {'id': wo.floor_id.id, 'name': wo.floor_id.name} if wo.floor_id else None,
                'space': {'id': wo.space_id.id, 'name': wo.space_id.name} if wo.space_id else None,
            },
            'team': wo.team_id.name if wo.team_id else None,
            'assigned_to': {'id': wo.assigned_user_id.id, 'name': wo.assigned_user_id.name} if wo.assigned_user_id else None,
            'contractor': {'id': wo.contractor_id.id, 'name': wo.contractor_id.name} if wo.contractor_id else None,
            'supervisor': wo.supervisor_id.name if wo.supervisor_id else None,
            'planned_start': wo.planned_start,
            'planned_end': wo.planned_end,
            'actual_start': wo.actual_start,
            'actual_end': wo.actual_end,
            'duration_hours': wo.duration_hours,
            'sla_deadline': wo.sla_deadline,
            'created_at': wo.create_date,
            'updated_at': wo.write_date,
        }

    def _serialize_work_order_detail(self, wo):
        """Extended serialization with checklist, materials, photos, messages."""
        data = self._serialize_work_order(wo)
        data['execution_result'] = wo.execution_result or ''
        data['delay_reason'] = wo.delay_reason or ''
        data['checklist'] = [{
            'id': c.id, 'name': c.name, 'is_done': c.is_done, 'notes': c.notes or '',
        } for c in wo.checklist_line_ids]
        data['materials'] = [{
            'id': m.id,
            'product_name': m.product_name or (m.product_id.name if m.product_id else ''),
            'quantity': m.quantity, 'uom': m.uom, 'cost': m.cost,
        } for m in wo.material_usage_ids]
        data['before_photos'] = [{
            'id': a.id, 'name': a.name, 'url': f'/web/content/{a.id}',
        } for a in wo.before_attachment_ids]
        data['after_photos'] = [{
            'id': a.id, 'name': a.name, 'url': f'/web/content/{a.id}',
        } for a in wo.after_attachment_ids]
        messages = wo.message_ids.filtered(
            lambda m: m.message_type in ('comment', 'notification'))[:20]
        data['messages'] = [{
            'id': m.id, 'body': m.body,
            'author': m.author_id.name if m.author_id else '', 'date': m.date,
        } for m in messages]
        return data

    def _is_manager(self, user):
        """Check if user has manager-level access."""
        return user._is_superuser() or user.facility_role in MANAGER_ROLES

    # ── Manager: All Requests ──────────────────────────────────
    @http.route('/api/v1/manager/requests', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def manager_list_requests(self, **kwargs):
        """List ALL requests (manager view, no requester filter)."""
        user = request.facility_user
        if not self._is_manager(user):
            return api_error('Unauthorized', status=403)

        env = request.facility_env
        page = int(kwargs.get('page', 1))
        limit = min(int(kwargs.get('limit', 20)), 100)
        offset = (page - 1) * limit
        domain = []

        if kwargs.get('request_type'):
            domain.append(('request_type', '=', kwargs['request_type']))
        if kwargs.get('state'):
            domain.append(('state', '=', kwargs['state']))
        if kwargs.get('priority'):
            domain.append(('priority', '=', kwargs['priority']))
        if kwargs.get('building_id'):
            domain.append(('building_id', '=', int(kwargs['building_id'])))
        if kwargs.get('search'):
            domain.append(('description', 'ilike', kwargs['search']))

        total = env['facility.request'].search_count(domain)
        requests = env['facility.request'].search(
            domain, limit=limit, offset=offset, order='create_date desc')

        from .api_requests import FacilityRequestAPI
        req_api = FacilityRequestAPI()
        data = [req_api._serialize_request(r) for r in requests]

        return api_response(data=data, meta={
            'page': page, 'limit': limit, 'total': total,
            'total_pages': (total + limit - 1) // limit,
        })

    # ── Manager: Request Detail ────────────────────────────────
    @http.route('/api/v1/manager/requests/<int:request_id>', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def manager_request_detail(self, request_id, **kwargs):
        """Get full request detail (manager view)."""
        user = request.facility_user
        if not self._is_manager(user):
            return api_error('Unauthorized', status=403)

        env = request.facility_env
        req = env['facility.request'].browse(request_id)
        if not req.exists():
            return api_error('Request not found', status=404)

        from .api_requests import FacilityRequestAPI
        req_api = FacilityRequestAPI()
        data = req_api._serialize_request(req)
        data['resolution_summary'] = req.resolution_summary
        data['rejection_reason'] = req.rejection_reason
        data['attachments'] = [{
            'id': a.id, 'name': a.name, 'mimetype': a.mimetype,
            'url': f'/web/content/{a.id}',
        } for a in req.attachment_ids]
        data['work_orders'] = [{
            'id': wo.id, 'name': wo.name, 'title': wo.title,
            'state': wo.state,
            'assigned_to': wo.assigned_user_id.name if wo.assigned_user_id else None,
        } for wo in req.work_order_ids]

        return api_response(data=data)

    # ── Manager: Dashboard KPIs ────────────────────────────────
    @http.route('/api/v1/manager/dashboard', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def manager_dashboard(self, **kwargs):
        """Extended dashboard KPIs for managers."""
        user = request.facility_user
        if not self._is_manager(user):
            return api_error('Unauthorized', status=403)

        env = request.facility_env
        total = env['facility.request'].search_count([])
        open_count = env['facility.request'].search_count(
            [('state', 'not in', ['closed', 'cancelled'])])
        overdue = env['facility.request'].search_count(
            [('is_overdue', '=', True)])
        solved = env['facility.request'].search_count(
            [('state', '=', 'solved')])
        closed = env['facility.request'].search_count(
            [('state', '=', 'closed')])

        # SLA compliance
        with_sla = env['facility.request'].search_count(
            [('sla_id', '!=', False), ('state', 'in', ['solved', 'closed'])])
        on_time = env['facility.request'].search_count(
            [('sla_id', '!=', False), ('state', 'in', ['solved', 'closed']),
             ('is_overdue', '=', False)])
        sla_pct = round((on_time / with_sla * 100) if with_sla else 0, 1)

        # Average rating
        ratings = env['facility.rating'].search([])
        avg_satisfaction = round(
            sum(r.average_score for r in ratings) / len(ratings), 1
        ) if ratings else 0.0

        # Work orders
        total_wo = env['facility.work.order'].search_count([])
        open_wo = env['facility.work.order'].search_count(
            [('state', 'not in', ['closed', 'cancelled'])])

        return api_response(data={
            'total_requests': total,
            'open_requests': open_count,
            'overdue_requests': overdue,
            'solved_requests': solved,
            'closed_requests': closed,
            'sla_compliance_pct': sla_pct,
            'avg_satisfaction': avg_satisfaction,
            'total_work_orders': total_wo,
            'open_work_orders': open_wo,
        })

    # ── Manager: Work Orders ───────────────────────────────────
    @http.route('/api/v1/manager/work-orders', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def manager_list_work_orders(self, **kwargs):
        """List ALL work orders (manager view)."""
        user = request.facility_user
        if not self._is_manager(user):
            return api_error('Unauthorized', status=403)

        env = request.facility_env
        page = int(kwargs.get('page', 1))
        limit = min(int(kwargs.get('limit', 20)), 100)
        offset = (page - 1) * limit
        domain = []

        if kwargs.get('state'):
            domain.append(('state', '=', kwargs['state']))
        if kwargs.get('priority'):
            domain.append(('priority', '=', kwargs['priority']))
        if kwargs.get('search'):
            domain.append(('title', 'ilike', kwargs['search']))

        total = env['facility.work.order'].search_count(domain)
        work_orders = env['facility.work.order'].search(
            domain, limit=limit, offset=offset, order='create_date desc')

        data = [self._serialize_work_order(wo) for wo in work_orders]
        return api_response(data=data, meta={
            'page': page, 'limit': limit, 'total': total,
            'total_pages': (total + limit - 1) // limit,
        })

    # ── Manager: Work Order Detail ─────────────────────────────
    @http.route('/api/v1/manager/work-orders/<int:wo_id>', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def manager_work_order_detail(self, wo_id, **kwargs):
        """Get full work order detail (manager view)."""
        user = request.facility_user
        if not self._is_manager(user):
            return api_error('Unauthorized', status=403)

        env = request.facility_env
        wo = env['facility.work.order'].browse(wo_id)
        if not wo.exists():
            return api_error('Work order not found', status=404)

        return api_response(data=self._serialize_work_order_detail(wo))

    # ── Technician: My Work Orders ─────────────────────────────
    @http.route('/api/v1/technician/work-orders', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def technician_work_orders(self, **kwargs):
        """List work orders assigned to the current technician."""
        env = request.facility_env
        user = request.facility_user

        page = int(kwargs.get('page', 1))
        limit = min(int(kwargs.get('limit', 20)), 100)
        offset = (page - 1) * limit
        domain = [('assigned_user_id', '=', user.id)]

        if kwargs.get('state'):
            domain.append(('state', '=', kwargs['state']))
        if kwargs.get('search'):
            domain.append(('title', 'ilike', kwargs['search']))

        total = env['facility.work.order'].search_count(domain)
        work_orders = env['facility.work.order'].search(
            domain, limit=limit, offset=offset, order='create_date desc')

        data = [self._serialize_work_order(wo) for wo in work_orders]
        return api_response(data=data, meta={
            'page': page, 'limit': limit, 'total': total,
            'total_pages': (total + limit - 1) // limit,
        })

    # ── Technician: Dashboard KPIs ─────────────────────────────
    @http.route('/api/v1/technician/dashboard', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def technician_dashboard(self, **kwargs):
        env = request.facility_env
        user = request.facility_user
        my_domain = [('assigned_user_id', '=', user.id)]

        total = env['facility.work.order'].search_count(my_domain)
        urgent = env['facility.work.order'].search_count(
            my_domain + [('priority', '=', 'urgent'),
                         ('state', 'not in', ['closed', 'cancelled'])])
        from odoo import fields as odoo_fields
        overdue = env['facility.work.order'].search_count(
            my_domain + [('sla_deadline', '<', odoo_fields.Datetime.now()),
                         ('state', 'not in', ['closed', 'completed', 'verified', 'cancelled'])])
        completed = env['facility.work.order'].search_count(
            my_domain + [('state', 'in', ['completed', 'verified', 'closed'])])

        return api_response(data={
            'total_tasks': total,
            'urgent_tasks': urgent,
            'overdue_tasks': overdue,
            'completed_tasks': completed,
        })

    # ── Technician: Work Order Detail ──────────────────────────
    @http.route('/api/v1/technician/work-orders/<int:wo_id>', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def technician_work_order_detail(self, wo_id, **kwargs):
        env = request.facility_env
        user = request.facility_user
        wo = env['facility.work.order'].browse(wo_id)
        if not wo.exists():
            return api_error('Work order not found', status=404)

        # Technician can only view their own assigned work orders
        if wo.assigned_user_id.id != user.id and not self._is_manager(user):
            return api_error('Unauthorized', status=403)

        return api_response(data=self._serialize_work_order_detail(wo))

    # ── Technician: Work Order Actions ─────────────────────────
    @http.route('/api/v1/technician/work-orders/<int:wo_id>/action', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @api_auth_required
    def technician_work_order_action(self, wo_id, **kwargs):
        """Perform action on work order: accept, start, pause, resume, complete."""
        try:
            data = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, TypeError):
            return api_error('Invalid data', status=400)

        env = request.facility_env
        user = request.facility_user
        wo = env['facility.work.order'].browse(wo_id)
        if not wo.exists():
            return api_error('Work order not found', status=404)

        # Technician can only act on their own assigned work orders
        if wo.assigned_user_id.id != user.id and not self._is_manager(user):
            return api_error('Unauthorized', status=403)

        action = data.get('action')
        action_map = {
            'accept': wo.action_accept,
            'start': wo.action_start,
            'pause': wo.action_pause,
            'resume': wo.action_resume,
            'complete': wo.action_complete,
        }
        fn = action_map.get(action)
        if not fn:
            return api_error('Invalid action', status=400)

        fn()
        return api_response(message='Action executed', data={'state': wo.state})

    # ── Contractor: Work Orders ────────────────────────────────
    @http.route('/api/v1/contractor/work-orders', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def contractor_work_orders(self, **kwargs):
        """List work orders assigned to the contractor's partner."""
        env = request.facility_env
        user = request.facility_user
        partner = user.partner_id

        page = int(kwargs.get('page', 1))
        limit = min(int(kwargs.get('limit', 20)), 100)
        offset = (page - 1) * limit
        domain = [('contractor_id', '=', partner.id)]

        if kwargs.get('state'):
            domain.append(('state', '=', kwargs['state']))

        total = env['facility.work.order'].search_count(domain)
        work_orders = env['facility.work.order'].search(
            domain, limit=limit, offset=offset, order='create_date desc')

        data = [self._serialize_work_order(wo) for wo in work_orders]
        return api_response(data=data, meta={
            'page': page, 'limit': limit, 'total': total,
            'total_pages': (total + limit - 1) // limit,
        })

    # ── Contractor: Work Order Detail ──────────────────────────
    @http.route('/api/v1/contractor/work-orders/<int:wo_id>', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def contractor_work_order_detail(self, wo_id, **kwargs):
        """Get work order detail (contractor view)."""
        env = request.facility_env
        user = request.facility_user
        partner = user.partner_id
        wo = env['facility.work.order'].browse(wo_id)
        if not wo.exists():
            return api_error('Work order not found', status=404)

        # Contractor can only view their own work orders
        if wo.contractor_id.id != partner.id and not self._is_manager(user):
            return api_error('Unauthorized', status=403)

        return api_response(data=self._serialize_work_order_detail(wo))

    # ── Contractor: Dashboard KPIs ─────────────────────────────
    @http.route('/api/v1/contractor/dashboard', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def contractor_dashboard(self, **kwargs):
        env = request.facility_env
        user = request.facility_user
        partner = user.partner_id
        domain = [('contractor_id', '=', partner.id)]

        total = env['facility.work.order'].search_count(domain)
        open_wo = env['facility.work.order'].search_count(
            domain + [('state', 'not in', ['closed', 'cancelled'])])
        completed = env['facility.work.order'].search_count(
            domain + [('state', 'in', ['completed', 'verified', 'closed'])])

        return api_response(data={
            'total_work_orders': total,
            'open_work_orders': open_wo,
            'completed_work_orders': completed,
        })
