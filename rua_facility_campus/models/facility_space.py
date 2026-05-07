# -*- coding: utf-8 -*-
from odoo import models, fields, api

# All 17 space types from the spec
SPACE_TYPE_SELECTION = [
    ('classroom', 'Classroom'),
    ('theater', 'Theater'),
    ('photo_studio', 'Photo Studio'),
    ('audio_studio', 'Audio Studio'),
    ('design_lab', 'Design Lab'),
    ('sculpture_workshop', 'Sculpture Workshop'),
    ('art_gallery', 'Art Gallery'),
    ('office', 'Office'),
    ('corridor', 'Corridor'),
    ('warehouse', 'Warehouse'),
    ('parking', 'Parking'),
    ('cafeteria', 'Cafeteria'),
    ('outdoor_area', 'Outdoor Area'),
    ('equipment_room', 'Equipment Room'),
    ('meeting_room', 'Meeting Room'),
    ('library', 'Library'),
    ('service_area', 'Service Area'),
]

READINESS_STATUS_SELECTION = [
    ('ready', 'Ready'),
    ('needs_cleaning', 'Needs Cleaning'),
    ('needs_maintenance', 'Needs Maintenance'),
    ('unavailable', 'Unavailable'),
    ('booked', 'Booked'),
    ('under_preparation', 'Under Preparation'),
    ('closed_for_safety', 'Closed for Safety'),
]


class FacilitySpace(models.Model):
    _name = 'facility.space'
    _description = 'Space'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'building_id, floor_id, name'

    name = fields.Char(string='Space Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)

    # Hierarchy
    campus_id = fields.Many2one('facility.campus', string='Campus',
                                 related='floor_id.campus_id', store=True)
    building_id = fields.Many2one('facility.building', string='Building',
                                   related='floor_id.building_id', store=True)
    floor_id = fields.Many2one('facility.floor', string='Floor',
                                required=True, ondelete='cascade')

    # Classification
    space_type = fields.Selection(SPACE_TYPE_SELECTION,
                                   string='Space Type', required=True, tracking=True)
    capacity = fields.Integer(string='Capacity')
    responsible_id = fields.Many2one('res.users', string='Responsible', tracking=True)

    # Status
    operational_status = fields.Selection([
        ('operational', 'Operational'),
        ('under_maintenance', 'Under Maintenance'),
        ('closed', 'Closed'),
    ], string='Operational Status', default='operational', tracking=True)

    readiness_status = fields.Selection(READINESS_STATUS_SELECTION,
                                         string='Readiness Status', default='ready',
                                         tracking=True)

    # Features
    is_bookable = fields.Boolean(string='Bookable', default=False)
    has_equipment = fields.Boolean(string='Has Equipment', default=False)
    safety_notes = fields.Text(string='Safety Notes')
    image = fields.Image(string='Image', max_width=1920, max_height=1080)
    notes = fields.Html(string='Notes')

    # Related
    asset_ids = fields.One2many('facility.asset', 'space_id', string='Assets')
    asset_count = fields.Integer(compute='_compute_asset_count')

    # Computed
    full_location = fields.Char(compute='_compute_full_location', string='Full Location',
                                 store=True)

    @api.depends('name', 'code', 'floor_id.name', 'building_id.name', 'campus_id.name')
    def _compute_full_location(self):
        for rec in self:
            parts = filter(None, [
                rec.campus_id.name,
                rec.building_id.name,
                rec.floor_id.name,
                rec.name,
            ])
            rec.full_location = ' ← '.join(parts)

    @api.depends('asset_ids')
    def _compute_asset_count(self):
        for rec in self:
            rec.asset_count = len(rec.asset_ids)
