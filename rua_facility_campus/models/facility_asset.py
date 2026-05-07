# -*- coding: utf-8 -*-
from odoo import models, fields, api


ASSET_STATUS_SELECTION = [
    ('working', 'Working'),
    ('needs_maintenance', 'Needs Maintenance'),
    ('under_maintenance', 'Under Maintenance'),
    ('out_of_service', 'Out of Service'),
    ('disposed', 'Disposed'),
    ('missing', 'Missing'),
    ('under_warranty', 'Under Warranty'),
]


class FacilityAsset(models.Model):
    _name = 'facility.asset'
    _description = 'Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Asset Name', required=True, tracking=True, translate=True)
    code = fields.Char(string='Asset Code', readonly=True, copy=False, default='New')
    active = fields.Boolean(default=True)

    # Classification
    asset_type = fields.Selection([
        ('operational', 'Operational'),
        ('educational', 'Educational / Artistic'),
    ], string='Asset Type', default='operational', required=True)

    asset_category_id = fields.Many2one('facility.asset.category',
                                         string='Asset Category')

    # Location
    campus_id = fields.Many2one('facility.campus', string='Campus',
                                 related='space_id.campus_id', store=True)
    building_id = fields.Many2one('facility.building', string='Building',
                                   related='space_id.building_id', store=True)
    floor_id = fields.Many2one('facility.floor', string='Floor',
                                related='space_id.floor_id', store=True)
    space_id = fields.Many2one('facility.space', string='Space', tracking=True)

    # Specifications
    manufacturer = fields.Char(string='Manufacturer')
    model_name = fields.Char(string='Model')
    serial_number = fields.Char(string='Serial Number')
    purchase_date = fields.Date(string='Purchase Date')
    installation_date = fields.Date(string='Installation Date')
    cost = fields.Float(string='Cost', digits=(12, 2))
    useful_life_years = fields.Integer(string='Useful Life (years)')

    # Status
    asset_status = fields.Selection(ASSET_STATUS_SELECTION,
                                     string='Asset Status', default='working',
                                     tracking=True, required=True)

    # Warranty
    warranty_start_date = fields.Date(string='Warranty Start')
    warranty_end_date = fields.Date(string='Warranty End')
    is_under_warranty = fields.Boolean(compute='_compute_warranty', string='Under Warranty')

    # Vendor
    vendor_id = fields.Many2one('res.partner', string='Vendor',
                                 domain=[('is_company', '=', True)])

    # Media
    qr_code = fields.Char(string='QR Code')
    image = fields.Image(string='Image', max_width=1920, max_height=1080)
    document_ids = fields.Many2many('ir.attachment', string='Documents')
    notes = fields.Html(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code(
                    'facility.asset') or 'New'
        return super().create(vals_list)

    @api.depends('warranty_end_date')
    def _compute_warranty(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_under_warranty = (
                rec.warranty_end_date and rec.warranty_end_date >= today
            )


class FacilityAssetCategory(models.Model):
    _name = 'facility.asset.category'
    _description = 'Asset Category'
    _order = 'name'

    name = fields.Char(string='Category', required=True, translate=True)
    parent_id = fields.Many2one('facility.asset.category', string='Parent Category')
    child_ids = fields.One2many('facility.asset.category', 'parent_id', string='Subcategories')
    icon = fields.Char(string='Icon')
