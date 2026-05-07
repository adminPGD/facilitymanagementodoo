# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FacilitySLA(models.Model):
    """SLA engine governing response and resolution times for requests and work orders."""
    _name = 'facility.sla'
    _description = 'Service Level Agreement'
    _order = 'sequence, name'

    name = fields.Char(string='SLA Name', required=True, translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    # Scope — which request types/priorities this SLA applies to
    request_type = fields.Selection([
        ('maintenance_report', 'Maintenance Report'),
        ('observation', 'Observation'),
        ('service_request', 'Service Request'),
        ('event_preparation', 'Event Preparation'),
        ('safety_report', 'Safety Report'),
        ('cleaning_request', 'Cleaning Request'),
        ('permit_request', 'Permit Request'),
    ], string='Request Type')

    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority')

    risk_level = fields.Selection([
        ('none', 'None'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Risk Level')

    # Time targets (in hours)
    response_time_hours = fields.Float(
        string='Response Time (hours)', default=4.0,
        help='Maximum time between request submission and first response')
    resolution_time_hours = fields.Float(
        string='Resolution Time (hours)', default=24.0,
        help='Maximum time between request submission and resolution')

    # Escalation
    escalation_level_1_user_id = fields.Many2one(
        'res.users', string='Level 1 Escalation',
        help='Escalated after response time expires')
    escalation_level_2_user_id = fields.Many2one(
        'res.users', string='Level 2 Escalation',
        help='Escalated after resolution time expires')

    notes = fields.Text(string='Notes')

    @api.model
    def find_matching_sla(self, request_type, priority, risk_level=False):
        """Find the most specific SLA matching the given criteria."""
        domain = [('active', '=', True)]
        # Try exact match first, then fallback to broader matches
        for rt in [request_type, False]:
            for pr in [priority, False]:
                for rl in [risk_level, False]:
                    search_domain = domain.copy()
                    if rt:
                        search_domain.append(('request_type', '=', rt))
                    else:
                        search_domain.append(('request_type', '=', False))
                    if pr:
                        search_domain.append(('priority', '=', pr))
                    else:
                        search_domain.append(('priority', '=', False))
                    if rl:
                        search_domain.append(('risk_level', '=', rl))
                    else:
                        search_domain.append(('risk_level', '=', False))
                    sla = self.search(search_domain, limit=1)
                    if sla:
                        return sla
        # Absolute fallback — first active SLA
        return self.search([('active', '=', True)], limit=1)
