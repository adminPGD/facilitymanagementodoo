# -*- coding: utf-8 -*-
from odoo import models, fields, api

WORK_ORDER_STATE_SELECTION = [
    ('new', 'New'),
    ('assigned', 'Assigned'),
    ('in_progress', 'In Progress'),
    ('paused', 'Paused'),
    ('waiting_parts', 'Waiting for Parts'),
    ('completed', 'Completed'),
    ('verified', 'Verified'),
    ('closed', 'Closed'),
    ('cancelled', 'Cancelled'),
]


class FacilityWorkOrder(models.Model):
    """Work order — the operational execution unit generated from requests."""
    _name = 'facility.work.order'
    _description = 'Work Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # === Identity ===
    name = fields.Char(string='Work Order Number', readonly=True, copy=False, default='New')
    title = fields.Char(string='Title', required=True, tracking=True)
    description = fields.Html(string='Description')
    state = fields.Selection(WORK_ORDER_STATE_SELECTION,
                              string='Status', default='new', tracking=True,
                              required=True, index=True)

    # === Source ===
    source_request_id = fields.Many2one('facility.request', string='Source Request',
                                         tracking=True, index=True)
    source_type = fields.Selection(related='source_request_id.request_type',
                                    string='Source Type', store=True)

    # === Location ===
    campus_id = fields.Many2one('facility.campus', string='Campus')
    building_id = fields.Many2one('facility.building', string='Building')
    floor_id = fields.Many2one('facility.floor', string='Floor')
    space_id = fields.Many2one('facility.space', string='Space')
    asset_id = fields.Many2one('facility.asset', string='Asset')

    # === Classification ===
    priority = fields.Selection([
        ('low', 'Low'), ('medium', 'Medium'),
        ('high', 'High'), ('urgent', 'Urgent'),
    ], string='Priority', default='medium', tracking=True)
    risk_level = fields.Selection([
        ('none', 'None'), ('low', 'Low'), ('medium', 'Medium'),
        ('high', 'High'), ('critical', 'Critical'),
    ], string='Risk Level', default='none')

    # === Assignment ===
    team_id = fields.Many2one('maintenance.team', string='Team', tracking=True)
    assigned_user_id = fields.Many2one('res.users', string='Assigned Technician', tracking=True)
    contractor_id = fields.Many2one('res.partner', string='Contractor',
                                     domain=[('is_company', '=', True)])
    supervisor_id = fields.Many2one('res.users', string='Supervisor', tracking=True)

    # === SLA ===
    sla_id = fields.Many2one('facility.sla', string='SLA')
    sla_deadline = fields.Datetime(string='SLA Deadline')

    # === Schedule ===
    planned_start = fields.Datetime(string='Planned Start')
    planned_end = fields.Datetime(string='Planned End')
    actual_start = fields.Datetime(string='Actual Start')
    actual_end = fields.Datetime(string='Actual End')
    duration_hours = fields.Float(string='Actual Duration (hours)',
                                   compute='_compute_duration', store=True)

    # === Execution ===
    before_attachment_ids = fields.Many2many(
        'ir.attachment', 'facility_wo_before_attach_rel', 'wo_id', 'attach_id',
        string='Before Photos')
    after_attachment_ids = fields.Many2many(
        'ir.attachment', 'facility_wo_after_attach_rel', 'wo_id', 'attach_id',
        string='After Photos')
    checklist_line_ids = fields.One2many('facility.work.order.checklist',
                                          'work_order_id', string='Checklist')
    material_usage_ids = fields.One2many('facility.material.usage',
                                          'work_order_id', string='Materials Used')

    execution_result = fields.Html(string='Execution Result')
    delay_reason = fields.Text(string='Delay Reason')
    verification_date = fields.Datetime(string='Verification Date')

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('actual_start', 'actual_end')
    def _compute_duration(self):
        for rec in self:
            if rec.actual_start and rec.actual_end:
                delta = rec.actual_end - rec.actual_start
                rec.duration_hours = delta.total_seconds() / 3600.0
            else:
                rec.duration_hours = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'facility.work.order') or 'New'
        return super().create(vals_list)

    # === Actions ===
    def action_assign(self):
        self.write({'state': 'assigned'})

    def action_accept(self):
        self.write({'state': 'in_progress', 'actual_start': fields.Datetime.now()})

    def action_start(self):
        self.write({'state': 'in_progress', 'actual_start': fields.Datetime.now()})

    def action_pause(self):
        self.write({'state': 'paused'})

    def action_resume(self):
        self.write({'state': 'in_progress'})

    def action_request_parts(self):
        self.write({'state': 'waiting_parts'})

    def action_complete(self):
        self.write({'state': 'completed', 'actual_end': fields.Datetime.now()})

    def action_verify(self):
        self.write({'state': 'verified', 'verification_date': fields.Datetime.now()})

    def action_close(self):
        self.write({'state': 'closed'})
        # Also update source request if all WOs are closed
        for rec in self:
            if rec.source_request_id:
                open_wos = rec.source_request_id.work_order_ids.filtered(
                    lambda w: w.state not in ('closed', 'cancelled') and w.id != rec.id)
                if not open_wos:
                    rec.source_request_id.action_solve()

    def action_cancel(self):
        self.write({'state': 'cancelled'})


class FacilityWorkOrderChecklist(models.Model):
    _name = 'facility.work.order.checklist'
    _description = 'Checklist Item'
    _order = 'sequence'

    work_order_id = fields.Many2one('facility.work.order', required=True,
                                     ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Item', required=True)
    is_done = fields.Boolean(string='Done')
    notes = fields.Char(string='Notes')


class FacilityMaterialUsage(models.Model):
    _name = 'facility.material.usage'
    _description = 'Material Usage'

    work_order_id = fields.Many2one('facility.work.order', required=True,
                                     ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    product_name = fields.Char(string='Material Name',
                                help='Used when product is not in the system')
    quantity = fields.Float(string='Quantity', default=1.0)
    uom = fields.Char(string='Unit', default='pc')
    cost = fields.Float(string='Cost', digits=(12, 2))
    notes = fields.Char(string='Notes')
