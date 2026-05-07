# -*- coding: utf-8 -*-
"""Request CRUD API endpoints with proper authorization checks."""
import json
import base64
from odoo import http
from odoo.http import request

from .api_auth import (
    api_response, api_error, api_auth_required,
    validate_file_upload, _get_portal_role,
)


class FacilityRequestAPI(http.Controller):

    def _serialize_request(self, req):
        """Serialize a facility.request record for API response."""
        return {
            'id': req.id,
            'name': req.name,
            'request_type': req.request_type,
            'state': req.state,
            'priority': req.priority,
            'risk_level': req.risk_level,
            'description': req.description or '',
            'category': {'id': req.category_id.id, 'name': req.category_id.name} if req.category_id else None,
            'location': {
                'campus': {'id': req.campus_id.id, 'name': req.campus_id.name} if req.campus_id else None,
                'building': {'id': req.building_id.id, 'name': req.building_id.name} if req.building_id else None,
                'floor': {'id': req.floor_id.id, 'name': req.floor_id.name} if req.floor_id else None,
                'space': {'id': req.space_id.id, 'name': req.space_id.name} if req.space_id else None,
            },
            'requester': {
                'id': req.requester_id.id,
                'name': req.requester_id.name,
                'role': req.requester_role,
            },
            'assigned_to': {'id': req.assigned_user_id.id, 'name': req.assigned_user_id.name} if req.assigned_user_id else None,
            'sla_deadline': req.sla_deadline,
            'is_overdue': req.is_overdue,
            'first_response_date': req.first_response_date,
            'close_date': req.close_date,
            'work_order_count': req.work_order_count,
            'created_at': req.create_date,
            'updated_at': req.write_date,
        }

    def _user_can_access_request(self, req, user):
        """Check if user can access a specific request."""
        role = _get_portal_role(user)
        if role in ('admin', 'manager'):
            return True
        if req.requester_id.id == user.id:
            return True
        if req.assigned_user_id and req.assigned_user_id.id == user.id:
            return True
        if user.facility_role == 'contractor' and req.contractor_id and req.contractor_id.id == user.partner_id.id:
            return True
        return False

    @http.route('/api/v1/requests', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def list_requests(self, **kwargs):
        """List requests for the current user with pagination and filters."""
        env = request.facility_env
        user = request.facility_user

        page = int(kwargs.get('page', 1))
        limit = min(int(kwargs.get('limit', 20)), 100)
        offset = (page - 1) * limit

        domain = [('requester_id', '=', user.id)]

        # Filters
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

        sort = kwargs.get('sort', 'create_date desc')
        if sort not in ('create_date desc', 'create_date asc', 'priority desc', 'priority asc'):
            sort = 'create_date desc'

        total = env['facility.request'].search_count(domain)
        requests = env['facility.request'].search(
            domain, limit=limit, offset=offset, order=sort)

        data = [self._serialize_request(r) for r in requests]
        return api_response(data=data, meta={
            'page': page, 'limit': limit, 'total': total,
            'total_pages': (total + limit - 1) // limit,
        })

    @http.route('/api/v1/requests/<int:request_id>', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def get_request(self, request_id, **kwargs):
        """Get single request details."""
        env = request.facility_env
        user = request.facility_user
        req = env['facility.request'].browse(request_id)
        if not req.exists():
            return api_error('Request not found', status=404)

        # Authorization: user must have access to this request
        if not self._user_can_access_request(req, user):
            return api_error('Unauthorized', status=403)

        data = self._serialize_request(req)
        # Add extra detail fields
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
        # Chatter messages
        messages = req.message_ids.filtered(
            lambda m: m.message_type in ('comment', 'notification'))[:20]
        data['messages'] = [{
            'id': m.id,
            'body': m.body,
            'author': m.author_id.name if m.author_id else '',
            'date': m.date,
        } for m in messages]
        return api_response(data=data)

    @http.route('/api/v1/requests', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @api_auth_required
    def create_request(self, **kwargs):
        """Create a new facility request."""
        try:
            data = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, TypeError):
            return api_error('Invalid data', status=400)

        required = ['request_type', 'description']
        errors = []
        for field in required:
            if not data.get(field):
                errors.append({'field': field, 'message': f'{field} is required'})
        if errors:
            return api_error('Missing required data', status=400, errors=errors)

        user = request.facility_user
        # requester_id is always set to current user — cannot be overridden
        vals = {
            'request_type': data['request_type'],
            'description': data['description'],
            'priority': data.get('priority', 'medium'),
            'risk_level': data.get('risk_level', 'none'),
            'campus_id': data.get('campus_id'),
            'building_id': data.get('building_id'),
            'floor_id': data.get('floor_id'),
            'space_id': data.get('space_id'),
            'asset_id': data.get('asset_id'),
            'category_id': data.get('category_id'),
            'subcategory_id': data.get('subcategory_id'),
            'department': data.get('department') or user.department_name,
            'college': data.get('college') or user.college_name,
            'source': 'portal',
            'requester_id': user.id,  # always current user
        }

        # Type-specific fields
        if data['request_type'] == 'event_preparation':
            for f in ['event_name', 'event_type', 'expected_attendees',
                       'event_start', 'event_end']:
                if data.get(f):
                    vals[f] = data[f]
            for svc in ['required_sound', 'required_lighting', 'required_photography',
                         'required_screen', 'required_chairs', 'required_stage',
                         'required_cleaning', 'required_security', 'required_hospitality',
                         'required_gallery_setup', 'required_technician']:
                vals[svc] = data.get(svc, False)

        elif data['request_type'] == 'service_request':
            for f in ['service_type', 'requested_date', 'requested_time',
                       'expected_duration']:
                if data.get(f):
                    vals[f] = data[f]

        elif data['request_type'] == 'observation':
            if data.get('observation_category'):
                vals['observation_category'] = data['observation_category']

        elif data['request_type'] == 'safety_report':
            if data.get('safety_risk_type'):
                vals['safety_risk_type'] = data['safety_risk_type']

        # Clean None values
        vals = {k: v for k, v in vals.items() if v is not None}

        # Convert ISO datetime strings (2026-05-30T17:00) to Odoo format (2026-05-30 17:00)
        for dt_field in ('event_start', 'event_end', 'requested_date'):
            if dt_field in vals and isinstance(vals[dt_field], str) and 'T' in vals[dt_field]:
                vals[dt_field] = vals[dt_field].replace('T', ' ')

        env = request.facility_env
        # sudo() needed because portal users don't have direct create rights
        # requester_id is hardcoded to current user above (cannot be overridden)
        req = env['facility.request'].sudo().create(vals)
        req.sudo().action_submit()

        return api_response(
            data=self._serialize_request(req),
            message='Request created successfully',
            status=201,
        )

    @http.route('/api/v1/requests/<int:request_id>/update', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @api_auth_required
    def update_request(self, request_id, **kwargs):
        """Update own draft/submitted request."""
        try:
            data = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, TypeError):
            return api_error('Invalid data', status=400)

        env = request.facility_env
        user = request.facility_user
        req = env['facility.request'].browse(request_id)
        if not req.exists():
            return api_error('Request not found', status=404)

        # Only requester can update, and only before acceptance
        if req.requester_id.id != user.id:
            return api_error('Unauthorized', status=403)
        if req.state not in ('draft', 'submitted'):
            return api_error('Cannot update request after acceptance', status=400)

        allowed_fields = {
            'description', 'priority', 'risk_level', 'campus_id', 'building_id',
            'floor_id', 'space_id', 'asset_id', 'category_id', 'subcategory_id',
            'event_name', 'event_type', 'expected_attendees', 'event_start', 'event_end',
            'service_type', 'requested_date', 'requested_time', 'expected_duration',
            'observation_category', 'safety_risk_type',
        }
        vals = {k: v for k, v in data.items() if k in allowed_fields and v is not None}

        if vals:
            req.sudo().write(vals)

        return api_response(
            data=self._serialize_request(req),
            message='Request updated',
        )

    @http.route('/api/v1/requests/<int:request_id>/comment', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @api_auth_required
    def add_comment(self, request_id, **kwargs):
        """Add a comment to a request's chatter."""
        try:
            data = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, TypeError):
            return api_error('Invalid data', status=400)

        env = request.facility_env
        user = request.facility_user
        req = env['facility.request'].browse(request_id)
        if not req.exists():
            return api_error('Request not found', status=404)

        # Authorization check
        if not self._user_can_access_request(req, user):
            return api_error('Unauthorized', status=403)

        body = data.get('body', '').strip()
        if not body:
            return api_error('Comment is required', status=400)

        req.message_post(body=body, message_type='comment',
                         subtype_xmlid='mail.mt_comment')
        return api_response(message='Comment added')

    @http.route('/api/v1/requests/<int:request_id>/cancel', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @api_auth_required
    def cancel_request(self, request_id, **kwargs):
        env = request.facility_env
        user = request.facility_user
        req = env['facility.request'].browse(request_id)
        if not req.exists():
            return api_error('Request not found', status=404)

        # Only requester or manager can cancel
        if req.requester_id.id != user.id and _get_portal_role(user) not in ('admin', 'manager'):
            return api_error('Unauthorized', status=403)

        req.action_cancel()
        return api_response(message='Request cancelled')

    @http.route('/api/v1/requests/<int:request_id>/reopen', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @api_auth_required
    def reopen_request(self, request_id, **kwargs):
        env = request.facility_env
        user = request.facility_user
        req = env['facility.request'].browse(request_id)
        if not req.exists():
            return api_error('Request not found', status=404)

        if req.requester_id.id != user.id and _get_portal_role(user) not in ('admin', 'manager'):
            return api_error('Unauthorized', status=403)

        req.action_reopen()
        return api_response(message='Request reopened')

    @http.route('/api/v1/requests/<int:request_id>/rating', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @api_auth_required
    def submit_rating(self, request_id, **kwargs):
        """Submit a rating for a completed request."""
        try:
            data = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, TypeError):
            return api_error('Invalid data', status=400)

        env = request.facility_env
        user = request.facility_user
        req = env['facility.request'].browse(request_id)
        if not req.exists():
            return api_error('Request not found', status=404)

        # Only the requester can rate their own request
        if req.requester_id.id != user.id:
            return api_error('Only the requester can rate this request', status=403)

        if req.state not in ('solved', 'closed'):
            return api_error('Rating available only after resolution', status=400)

        # sudo() needed: portal users don't have create rights on facility.rating
        # rated_by is always set to current user
        rating = env['facility.rating'].sudo().create({
            'request_id': req.id,
            'rated_by': user.id,  # always current user
            'response_speed': str(data.get('response_speed', 3)),
            'execution_quality': str(data.get('execution_quality', 3)),
            'team_behavior': str(data.get('team_behavior', 3)),
            'issue_solved': data.get('issue_solved', True),
            'comment': data.get('comment', ''),
            'reopen_requested': data.get('reopen_requested', False),
        })
        req.sudo().write({'rating_id': rating.id})

        return api_response(message='Thank you for your rating', data={'rating_id': rating.id})

    @http.route('/api/v1/requests/<int:request_id>/attachments', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @api_auth_required
    def upload_attachment(self, request_id, **kwargs):
        """Upload file attachments to a request with validation."""
        env = request.facility_env
        user = request.facility_user
        req = env['facility.request'].browse(request_id)
        if not req.exists():
            return api_error('Request not found', status=404)

        # Authorization: only requester or managers can upload
        if req.requester_id.id != user.id and _get_portal_role(user) not in ('admin', 'manager'):
            return api_error('Unauthorized', status=403)

        files = request.httprequest.files.getlist('files')
        if not files:
            return api_error('No files provided', status=400)

        # Validate files
        file_errors = validate_file_upload(files)
        if file_errors:
            return api_error('File validation failed', status=400, errors=file_errors)

        attachment_ids = []
        for f in files:
            data = base64.b64encode(f.read())
            # sudo() needed: portal users don't have create rights on ir.attachment
            # res_model/res_id are hardcoded to facility.request — cannot be overridden
            attach = env['ir.attachment'].sudo().create({
                'name': f.filename,
                'datas': data,
                'res_model': 'facility.request',
                'res_id': req.id,
            })
            attachment_ids.append(attach.id)

        req.sudo().write({
            'attachment_ids': [(4, aid) for aid in attachment_ids]
        })

        return api_response(
            message='Attachments uploaded successfully',
            data={'attachment_ids': attachment_ids},
            status=201,
        )

    @http.route('/api/v1/reports/dashboard', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def dashboard_stats(self, **kwargs):
        """Dashboard KPIs for the portal — rich stats for modern dashboard."""
        env = request.facility_env
        user = request.facility_user
        role = _get_portal_role(user)

        # Managers, admins, technicians, supervisors see ALL requests
        if role in ('admin', 'manager', 'technician', 'supervisor'):
            user_domain = []
        else:
            user_domain = [('requester_id', '=', user.id)]

        total = env['facility.request'].search_count(user_domain)
        open_count = env['facility.request'].search_count(
            user_domain + [('state', 'not in', ['closed', 'cancelled'])])
        overdue = env['facility.request'].search_count(
            user_domain + [('is_overdue', '=', True)])
        solved = env['facility.request'].search_count(
            user_domain + [('state', '=', 'solved')])
        in_progress = env['facility.request'].search_count(
            user_domain + [('state', '=', 'in_progress')])
        closed = env['facility.request'].search_count(
            user_domain + [('state', '=', 'closed')])

        # --- Request type breakdown ---
        type_breakdown = []
        for ttype, tlabel in [
            ('maintenance_report', 'Maintenance Report'),
            ('observation', 'Observation'),
            ('service_request', 'Service Request'),
            ('event_preparation', 'Event Preparation'),
            ('safety_report', 'Safety Report'),
            ('cleaning_request', 'Cleaning Request'),
        ]:
            cnt = env['facility.request'].search_count(
                user_domain + [('request_type', '=', ttype)])
            if cnt:
                type_breakdown.append({'type': ttype, 'label': tlabel, 'count': cnt})

        # --- Priority distribution ---
        priority_breakdown = []
        for pri, plabel in [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')]:
            cnt = env['facility.request'].search_count(
                user_domain + [('priority', '=', pri)])
            if cnt:
                priority_breakdown.append({'priority': pri, 'label': plabel, 'count': cnt})

        # --- State distribution ---
        state_breakdown = []
        for st, slabel in [('draft', 'Draft'), ('submitted', 'Submitted'), ('accepted', 'Accepted'),
                           ('in_progress', 'In Progress'), ('solved', 'Solved'),
                           ('closed', 'Closed'), ('cancelled', 'Cancelled')]:
            cnt = env['facility.request'].search_count(
                user_domain + [('state', '=', st)])
            if cnt:
                state_breakdown.append({'state': st, 'label': slabel, 'count': cnt})

        # --- Recent requests (last 5) ---
        recent_reqs = env['facility.request'].search(
            user_domain, limit=5, order='create_date desc')
        recent = [{
            'id': r.id,
            'name': r.name,
            'request_type': r.request_type,
            'state': r.state,
            'priority': r.priority,
            'description': (r.description or '')[:80],
            'location': r.space_id.name if r.space_id else (r.building_id.name if r.building_id else ''),
            'created_at': str(r.create_date),
        } for r in recent_reqs]

        # --- Monthly trend (last 6 months) ---
        from datetime import datetime, timedelta
        monthly_trend = []
        now = datetime.now()
        for i in range(5, -1, -1):
            d = now - timedelta(days=i * 30)
            month_start = d.replace(day=1, hour=0, minute=0, second=0)
            if i > 0:
                next_month = (d + timedelta(days=32)).replace(day=1, hour=0, minute=0, second=0)
            else:
                next_month = now
            cnt = env['facility.request'].search_count(
                user_domain + [
                    ('create_date', '>=', month_start.strftime('%Y-%m-%d')),
                    ('create_date', '<', next_month.strftime('%Y-%m-%d')),
                ])
            monthly_trend.append({
                'month': month_start.strftime('%Y-%m'),
                'label': month_start.strftime('%b'),
                'count': cnt,
            })

        return api_response(data={
            'total_requests': total,
            'open_requests': open_count,
            'overdue_requests': overdue,
            'solved_requests': solved,
            'in_progress_requests': in_progress,
            'closed_requests': closed,
            'type_breakdown': type_breakdown,
            'priority_breakdown': priority_breakdown,
            'state_breakdown': state_breakdown,
            'recent_requests': recent,
            'monthly_trend': monthly_trend,
        })

