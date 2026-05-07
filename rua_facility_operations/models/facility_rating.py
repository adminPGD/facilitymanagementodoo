# -*- coding: utf-8 -*-
from odoo import models, fields


class FacilityRating(models.Model):
    """User rating/evaluation after request resolution."""
    _name = 'facility.rating'
    _description = 'Service Rating'
    _order = 'rating_date desc'

    request_id = fields.Many2one('facility.request', string='Request',
                                  required=True, ondelete='cascade')
    work_order_id = fields.Many2one('facility.work.order', string='Work Order')
    rated_by = fields.Many2one('res.users', string='Rated By',
                                default=lambda self: self.env.user)

    # Rating dimensions (1-5)
    response_speed = fields.Selection([
        ('1', '⭐'), ('2', '⭐⭐'), ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'), ('5', '⭐⭐⭐⭐⭐'),
    ], string='Response Speed', required=True)
    execution_quality = fields.Selection([
        ('1', '⭐'), ('2', '⭐⭐'), ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'), ('5', '⭐⭐⭐⭐⭐'),
    ], string='Execution Quality', required=True)
    team_behavior = fields.Selection([
        ('1', '⭐'), ('2', '⭐⭐'), ('3', '⭐⭐⭐'),
        ('4', '⭐⭐⭐⭐'), ('5', '⭐⭐⭐⭐⭐'),
    ], string='Team Behavior', required=True)
    issue_solved = fields.Boolean(string='Issue Resolved?', default=True)

    comment = fields.Text(string='Comment')
    reopen_requested = fields.Boolean(string='Reopen Requested', default=False)
    rating_date = fields.Datetime(string='Rating Date',
                                   default=fields.Datetime.now)

    # Computed average
    average_score = fields.Float(compute='_compute_average', string='Average Score',
                                  store=True, digits=(3, 1))

    def _compute_average(self):
        for rec in self:
            scores = [
                int(rec.response_speed or '0'),
                int(rec.execution_quality or '0'),
                int(rec.team_behavior or '0'),
            ]
            valid = [s for s in scores if s > 0]
            rec.average_score = sum(valid) / len(valid) if valid else 0.0
