# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    facility_default_sla_id = fields.Many2one(
        'facility.sla', string='Default SLA',
        config_parameter='rua_facility.default_sla_id')
    facility_auto_assign_team = fields.Boolean(
        string='Auto-assign Team',
        config_parameter='rua_facility.auto_assign_team',
        help='Automatically assign team based on request type and location')
    facility_allow_reopen = fields.Boolean(
        string='Allow Reopening Requests',
        config_parameter='rua_facility.allow_reopen',
        default=True)
    facility_rating_required = fields.Boolean(
        string='Rating Required After Closure',
        config_parameter='rua_facility.rating_required',
        default=True)
    facility_max_attachment_size_mb = fields.Integer(
        string='Max Attachment Size (MB)',
        config_parameter='rua_facility.max_attachment_size_mb',
        default=10)
