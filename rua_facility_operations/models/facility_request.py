# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

REQUEST_TYPE_SELECTION = [
    ('maintenance_report', 'Maintenance Report'),
    ('observation', 'Observation'),
    ('service_request', 'Service Request'),
    ('event_preparation', 'Event Preparation'),
    ('safety_report', 'Safety Report'),
    ('cleaning_request', 'Cleaning Request'),
    ('permit_request', 'Permit Request'),
]

REQUEST_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('accepted', 'Accepted'),
    ('in_progress', 'In Progress'),
    ('solved', 'Solved'),
    ('closed', 'Closed'),
    ('cancelled', 'Cancelled'),
]

PRIORITY_SELECTION = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('urgent', 'Urgent'),
]

RISK_LEVEL_SELECTION = [
    ('none', 'None'),
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

SOURCE_SELECTION = [
    ('portal', 'User Portal'),
    ('backend', 'Admin System'),
    ('phone', 'Phone Call'),
    ('walkin', 'Walk-in'),
    ('inspection', 'Inspection'),
    ('preventive', 'Preventive Maintenance'),
]


class FacilityRequest(models.Model):
    """Unified request model for all facility management request types."""
    _name = 'facility.request'
    _description = 'Facility Management Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'

    # === Identity ===
    name = fields.Char(string='Request Number', readonly=True, copy=False, default='New')
    request_type = fields.Selection(REQUEST_TYPE_SELECTION,
                                     string='Request Type', required=True, tracking=True)
    state = fields.Selection(REQUEST_STATE_SELECTION,
                              string='Status', default='draft', tracking=True,
                              required=True, index=True)

    # === Requester ===
    requester_id = fields.Many2one('res.users', string='Requester',
                                    default=lambda self: self.env.user, tracking=True)
    requester_partner_id = fields.Many2one('res.partner', string='Partner',
                                            related='requester_id.partner_id', store=True)
    requester_role = fields.Selection(related='requester_id.facility_role',
                                      string='Requester Role', store=True)
    department = fields.Char(string='Department')
    college = fields.Char(string='College')

    # === Location ===
    campus_id = fields.Many2one('facility.campus', string='Campus', tracking=True)
    building_id = fields.Many2one('facility.building', string='Building')
    floor_id = fields.Many2one('facility.floor', string='Floor')
    space_id = fields.Many2one('facility.space', string='Space')
    asset_id = fields.Many2one('facility.asset', string='Asset')

    # === Classification ===
    category_id = fields.Many2one('facility.request.category', string='Category')
    subcategory_id = fields.Many2one('facility.request.subcategory', string='Subcategory')
    priority = fields.Selection(PRIORITY_SELECTION,
                                 string='Priority', default='medium', tracking=True)
    risk_level = fields.Selection(RISK_LEVEL_SELECTION,
                                   string='Risk Level', default='none', tracking=True)

    # === Content ===
    description = fields.Html(string='Description', required=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    # === Assignment ===
    assigned_team_id = fields.Many2one('maintenance.team', string='Assigned Team',
                                       tracking=True)
    assigned_user_id = fields.Many2one('res.users', string='Assigned To', tracking=True)
    contractor_id = fields.Many2one('res.partner', string='Contractor',
                                     domain=[('is_company', '=', True)])

    # === SLA ===
    sla_id = fields.Many2one('facility.sla', string='SLA')
    sla_deadline = fields.Datetime(string='SLA Deadline', tracking=True)
    first_response_date = fields.Datetime(string='First Response Date')
    is_overdue = fields.Boolean(compute='_compute_is_overdue', string='Overdue',
                                 store=True, compute_sudo=True)

    # === Resolution ===
    close_date = fields.Datetime(string='Close Date')
    resolution_summary = fields.Html(string='Resolution Summary')
    rejection_reason = fields.Text(string='Rejection Reason')
    delay_reason = fields.Text(string='Delay Reason')

    # === Source & Meta ===
    source = fields.Selection(SOURCE_SELECTION, string='Request Source', default='portal')

    # === Related ===
    work_order_ids = fields.One2many('facility.work.order', 'source_request_id',
                                     string='Work Orders')
    work_order_count = fields.Integer(compute='_compute_work_order_count',
                                       string='Work Order Count')
    rating_id = fields.Many2one('facility.rating', string='Rating')

    # === Service Request specific fields ===
    service_type = fields.Selection([
        ('clean_space', 'Clean Space'),
        ('move_furniture', 'Move Furniture'),
        ('prepare_room', 'Prepare Room'),
        ('request_equipment', 'Request Equipment'),
        ('technical_support', 'Technical Support'),
        ('theater_support', 'Theater Support'),
        ('studio_support', 'Studio Support'),
        ('security_organization', 'Security & Organization'),
        ('contractor_entry_permit', 'Contractor Entry Permit'),
        ('open_space', 'Open Space'),
        ('prepare_gallery', 'Prepare Gallery'),
    ], string='Service Type')
    requested_date = fields.Date(string='Requested Date')
    requested_time = fields.Float(string='Requested Time')
    expected_duration = fields.Float(string='Expected Duration (hours)')

    # === Observation specific fields ===
    observation_category = fields.Selection([
        ('improvement', 'Improvement'),
        ('cleanliness', 'Cleanliness'),
        ('user_experience', 'User Experience'),
        ('safety', 'Safety'),
        ('suggestion', 'Suggestion'),
        ('signage', 'Signage'),
        ('accessibility', 'Accessibility'),
        ('space_quality', 'Space Quality'),
    ], string='Observation Category')

    # === Event Preparation specific fields ===
    event_name = fields.Char(string='Event Name')
    event_type = fields.Selection([
        ('art_exhibition', 'Art Exhibition'),
        ('theater_show', 'Theater Show'),
        ('music_show', 'Music Show'),
        ('workshop', 'Workshop'),
        ('lecture', 'Lecture'),
        ('ceremony', 'Ceremony'),
        ('student_event', 'Student Event'),
        ('official_event', 'Official Event'),
        ('filming_production', 'Filming Production'),
    ], string='Event Type')
    event_start = fields.Datetime(string='Event Start')
    event_end = fields.Datetime(string='Event End')
    expected_attendees = fields.Integer(string='Expected Attendees')
    # Services checkboxes
    required_sound = fields.Boolean(string='Sound System')
    required_lighting = fields.Boolean(string='Specialized Lighting')
    required_photography = fields.Boolean(string='Photography & Documentation')
    required_screen = fields.Boolean(string='Display Screens')
    required_chairs = fields.Boolean(string='Seating Arrangement')
    required_stage = fields.Boolean(string='Stage')
    required_cleaning = fields.Boolean(string='Deep Cleaning')
    required_security = fields.Boolean(string='Security & Organization')
    required_hospitality = fields.Boolean(string='Hospitality')
    required_gallery_setup = fields.Boolean(string='Gallery Setup')
    required_technician = fields.Boolean(string='Specialized Technician')

    # === Safety report specific ===
    safety_risk_type = fields.Selection([
        ('blocked_emergency_exit', 'Blocked Emergency Exit'),
        ('exposed_wire', 'Exposed Wire'),
        ('slippery_floor', 'Slippery Floor'),
        ('fire_smell', 'Fire/Smoke Smell'),
        ('unsafe_equipment', 'Unsafe Equipment'),
        ('workshop_incident', 'Workshop Incident'),
        ('injury', 'Injury'),
        ('theater_or_studio_hazard', 'Theater/Studio Hazard'),
        ('other', 'Other'),
    ], string='Safety Risk Type')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # === Computed ===
    @api.depends('sla_deadline', 'state')
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        for rec in self:
            rec.is_overdue = (
                rec.sla_deadline
                and rec.sla_deadline < now
                and rec.state not in ('solved', 'closed', 'cancelled')
            )

    @api.depends('work_order_ids')
    def _compute_work_order_count(self):
        for rec in self:
            rec.work_order_count = len(rec.work_order_ids)

    # === CRUD ===
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'facility.request') or 'New'
        return super().create(vals_list)

    # === Actions ===
    def action_submit(self):
        """Submit request and calculate SLA deadline."""
        for rec in self:
            # Find matching SLA
            sla = self.env['facility.sla'].find_matching_sla(
                rec.request_type, rec.priority, rec.risk_level)
            vals = {'state': 'submitted'}
            if sla:
                vals['sla_id'] = sla.id
                vals['sla_deadline'] = fields.Datetime.now() + timedelta(
                    hours=sla.resolution_time_hours)
            rec.write(vals)

    def action_accept(self):
        for rec in self:
            vals = {'state': 'accepted'}
            if not rec.first_response_date:
                vals['first_response_date'] = fields.Datetime.now()
            rec.write(vals)

    def action_reject(self):
        self.write({'state': 'cancelled'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_solve(self):
        self.write({'state': 'solved'})

    def action_close(self):
        self.write({
            'state': 'closed',
            'close_date': fields.Datetime.now(),
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reopen(self):
        self.write({'state': 'submitted'})

    def action_create_work_order(self):
        """Create a work order from this request."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Work Order'),
            'res_model': 'facility.work.order',
            'view_mode': 'form',
            'context': {
                'default_source_request_id': self.id,
                'default_source_type': self.request_type,
                'default_title': self.name,
                'default_description': self.description,
                'default_campus_id': self.campus_id.id,
                'default_building_id': self.building_id.id,
                'default_floor_id': self.floor_id.id,
                'default_space_id': self.space_id.id,
                'default_asset_id': self.asset_id.id,
                'default_priority': self.priority,
                'default_risk_level': self.risk_level,
            },
        }

    # === Cron ===
    @api.model
    def _cron_check_sla(self):
        """Check for overdue requests and trigger escalation notifications."""
        overdue = self.search([
            ('is_overdue', '=', True),
            ('state', 'not in', ['solved', 'closed', 'cancelled']),
        ])
        for req in overdue:
            if req.sla_id.escalation_level_1_user_id:
                req.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=req.sla_id.escalation_level_1_user_id.id,
                    note=_('Request %s has exceeded SLA deadline', req.name),
                )


class FacilityRequestCategory(models.Model):
    _name = 'facility.request.category'
    _description = 'Request Category'
    _order = 'name'

    name = fields.Char(string='Category', required=True, translate=True)
    icon = fields.Char(string='Icon')
    subcategory_ids = fields.One2many('facility.request.subcategory', 'category_id',
                                      string='Subcategories')


class FacilityRequestSubcategory(models.Model):
    _name = 'facility.request.subcategory'
    _description = 'Request Subcategory'
    _order = 'name'

    name = fields.Char(string='Subcategory', required=True, translate=True)
    category_id = fields.Many2one('facility.request.category', string='Parent Category',
                                   required=True, ondelete='cascade')
