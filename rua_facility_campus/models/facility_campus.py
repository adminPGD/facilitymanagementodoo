# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FacilityCampus(models.Model):
    _name = 'facility.campus'
    _description = 'Campus'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Campus Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    city = fields.Char(string='City', default='Riyadh')
    address = fields.Text(string='Address')
    manager_id = fields.Many2one('res.users', string='Campus Manager', tracking=True)
    notes = fields.Html(string='Notes')
    image = fields.Image(string='Image', max_width=1920, max_height=1080)
    map_attachment_id = fields.Many2one('ir.attachment', string='Campus Map')

    # Hierarchy
    building_ids = fields.One2many('facility.building', 'campus_id', string='Buildings')
    building_count = fields.Integer(compute='_compute_counts', string='Building Count')
    space_count = fields.Integer(compute='_compute_counts', string='Space Count')

    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)

    @api.depends('building_ids', 'building_ids.floor_ids.space_ids')
    def _compute_counts(self):
        for rec in self:
            rec.building_count = len(rec.building_ids)
            rec.space_count = self.env['facility.space'].search_count(
                [('campus_id', '=', rec.id)])


class FacilityBuilding(models.Model):
    _name = 'facility.building'
    _description = 'Building'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Building Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Building Code', required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    campus_id = fields.Many2one('facility.campus', string='Campus',
                                 required=True, ondelete='cascade')

    building_type = fields.Selection([
        ('academic', 'Academic'),
        ('administrative', 'Administrative'),
        ('service', 'Service'),
        ('residential', 'Residential'),
        ('mixed', 'Mixed'),
    ], string='Building Type', default='academic')

    manager_id = fields.Many2one('res.users', string='Building Manager', tracking=True)
    total_floors = fields.Integer(string='Total Floors', compute='_compute_floor_count')

    operational_status = fields.Selection([
        ('operational', 'Operational'),
        ('partial', 'Partially Operational'),
        ('under_construction', 'Under Construction'),
        ('closed', 'Closed'),
    ], string='Operational Status', default='operational', tracking=True)

    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))
    image = fields.Image(string='Image', max_width=1920, max_height=1080)
    notes = fields.Html(string='Notes')

    floor_ids = fields.One2many('facility.floor', 'building_id', string='Floors')

    @api.depends('floor_ids')
    def _compute_floor_count(self):
        for rec in self:
            rec.total_floors = len(rec.floor_ids)
