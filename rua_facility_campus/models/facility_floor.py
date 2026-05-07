# -*- coding: utf-8 -*-
from odoo import models, fields, api


class FacilityFloor(models.Model):
    _name = 'facility.floor'
    _description = 'Floor'
    _order = 'building_id, floor_number, name'

    name = fields.Char(string='Floor Name', required=True, translate=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)
    floor_number = fields.Integer(string='Floor Number', default=0,
                                   help='0 = Ground, -1 = Basement')

    building_id = fields.Many2one('facility.building', string='Building',
                                   required=True, ondelete='cascade')
    campus_id = fields.Many2one('facility.campus', string='Campus',
                                 related='building_id.campus_id', store=True)

    map_attachment_id = fields.Many2one('ir.attachment', string='Floor Plan')
    operational_status = fields.Selection([
        ('operational', 'Operational'),
        ('partial', 'Partially Operational'),
        ('closed', 'Closed'),
    ], string='Status', default='operational')
    notes = fields.Html(string='Notes')

    space_ids = fields.One2many('facility.space', 'floor_id', string='Spaces')
    space_count = fields.Integer(compute='_compute_space_count', string='Space Count')

    @api.depends('space_ids')
    def _compute_space_count(self):
        for rec in self:
            rec.space_count = len(rec.space_ids)
