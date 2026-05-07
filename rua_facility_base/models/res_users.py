# -*- coding: utf-8 -*-
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    # University identity
    national_id = fields.Char(string='National ID')
    university_id = fields.Char(string='University ID')
    phone_mobile = fields.Char(string='Mobile Phone')

    # Facility role — determines portal experience
    facility_role = fields.Selection([
        ('student', 'Student'),
        ('faculty', 'Faculty Member'),
        ('employee', 'Employee'),
        ('technician', 'Technician'),
        ('facility_supervisor', 'Facility Supervisor'),
        ('facility_manager', 'Facility Manager'),
        ('contractor', 'Contractor'),
        ('contract_officer', 'Contract Officer'),
        ('sustainability_officer', 'Sustainability Officer'),
        ('safety_officer', 'Safety Officer'),
        ('management', 'University Management'),
    ], string='Facility Role')

    department_name = fields.Char(string='Department')
    college_name = fields.Char(string='College')
