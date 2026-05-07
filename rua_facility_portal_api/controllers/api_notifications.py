# -*- coding: utf-8 -*-
"""Notification API endpoints."""
import json
from odoo import http
from odoo.http import request

from .api_auth import api_response, api_error, api_auth_required


class FacilityNotificationAPI(http.Controller):

    @http.route('/api/v1/notifications', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def list_notifications(self, **kwargs):
        """List notifications for the current user (from mail.message)."""
        env = request.facility_env
        user = request.facility_user

        page = int(kwargs.get('page', 1))
        limit = min(int(kwargs.get('limit', 20)), 50)
        offset = (page - 1) * limit

        # Get notifications targeted at this user
        domain = [
            ('partner_ids', 'in', [user.partner_id.id]),
            ('message_type', 'in', ['notification', 'comment']),
        ]
        total = env['mail.message'].search_count(domain)
        messages = env['mail.message'].search(
            domain, limit=limit, offset=offset, order='date desc')

        # Get read status for each message
        read_notifs = env['mail.notification'].sudo().search([
            ('res_partner_id', '=', user.partner_id.id),
            ('mail_message_id', 'in', messages.ids),
            ('is_read', '=', True),
        ])
        read_message_ids = set(read_notifs.mapped('mail_message_id').ids)

        # Count unread
        unread_count = env['mail.notification'].sudo().search_count([
            ('res_partner_id', '=', user.partner_id.id),
            ('is_read', '=', False),
        ])

        data = [{
            'id': m.id,
            'subject': m.subject or '',
            'body': m.body,
            'date': m.date,
            'model': m.model,
            'res_id': m.res_id,
            'author': m.author_id.name if m.author_id else '',
            'is_read': m.id in read_message_ids,
        } for m in messages]

        return api_response(data=data, meta={
            'page': page, 'limit': limit, 'total': total,
            'total_pages': (total + limit - 1) // limit,
            'unread_count': unread_count,
        })

    @http.route('/api/v1/notifications/<int:notification_id>/read', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def mark_single_read(self, notification_id, **kwargs):
        """Mark a single notification as read."""
        env = request.facility_env
        user = request.facility_user

        notif_domain = [
            ('res_partner_id', '=', user.partner_id.id),
            ('mail_message_id', '=', notification_id),
            ('is_read', '=', False),
        ]
        notifications = env['mail.notification'].sudo().search(notif_domain)
        if notifications:
            notifications.write({'is_read': True})

        return api_response(message='Notification marked as read')

    @http.route('/api/v1/notifications/mark-read', type='http', auth='none',
                methods=['POST'], csrf=False, cors='*')
    @api_auth_required
    def mark_notifications_read(self, **kwargs):
        """Mark specific notifications as read by IDs."""
        try:
            data = json.loads(request.httprequest.data)
        except (json.JSONDecodeError, TypeError):
            return api_error('Invalid data', status=400)

        env = request.facility_env
        user = request.facility_user
        ids = data.get('ids', [])

        if not ids:
            return api_error('Notification IDs are required', status=400)

        notif_domain = [
            ('res_partner_id', '=', user.partner_id.id),
            ('is_read', '=', False),
            ('mail_message_id', 'in', ids),
        ]

        notifications = env['mail.notification'].sudo().search(notif_domain)
        if notifications:
            notifications.write({'is_read': True})

        return api_response(message='Notifications marked as read')

    @http.route('/api/v1/notifications/read-all', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    @api_auth_required
    def mark_all_read(self, **kwargs):
        """Mark all notifications as read for the current user."""
        env = request.facility_env
        user = request.facility_user

        notif_domain = [
            ('res_partner_id', '=', user.partner_id.id),
            ('is_read', '=', False),
        ]
        notifications = env['mail.notification'].sudo().search(notif_domain)
        count = len(notifications)
        if notifications:
            notifications.write({'is_read': True})

        return api_response(
            message='All notifications marked as read',
            data={'count': count},
        )
