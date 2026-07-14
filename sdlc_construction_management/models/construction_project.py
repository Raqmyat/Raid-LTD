from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ConstructionProject(models.Model):
    _name = 'construction.project'
    _description = 'Construction Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Project Name', required=True, tracking=True)
    reference = fields.Char(string='Reference', readonly=True, default='New', copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # Address
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Suite/Apt')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State/Province')
    zip = fields.Char(string='ZIP Code')
    country_id = fields.Many2one('res.country', string='Country')

    # Duration
    date_start = fields.Date(string='Start Date', tracking=True)
    date_end = fields.Date(string='End Date', tracking=True)

    # Location
    longitude = fields.Float(string='Longitude', digits=(16, 6))
    latitude = fields.Float(string='Latitude', digits=(16, 6))

    # Contact
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('short_closed', 'Short Closed'),
    ], string='Status', default='draft', tracking=True)

    # Relational
    sub_project_ids = fields.One2many('construction.sub.project', 'project_id', string='Sub Projects')
    image_ids = fields.One2many('construction.project.image', 'project_id', string='Images')

    # Computed
    sub_project_count = fields.Integer(compute='_compute_counts', string='Sub Projects')
    budget_count = fields.Integer(compute='_compute_counts', string='Budgets')
    work_order_count = fields.Integer(compute='_compute_counts', string='Work Orders')
    mreq_count = fields.Integer(compute='_compute_counts', string='Material Requisitions')
    task_count = fields.Integer(compute='_compute_counts', string='Tasks')
    phase_count = fields.Integer(compute='_compute_counts', string='Phases')
    expense_count = fields.Integer(compute='_compute_counts', string='Expenses')

    # Permits
    permit_ids = fields.One2many('construction.permit', 'project_id', string='Permits & Approvals')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('construction.project') or 'New'
        return super().create(vals_list)

    def _compute_counts(self):
        for rec in self:
            rec.sub_project_count = self.env['construction.sub.project'].search_count([('project_id', '=', rec.id)])
            rec.budget_count = self.env['construction.budget'].search_count([('project_id', '=', rec.id)])
            rec.work_order_count = self.env['construction.work.order'].search_count([('project_id', '=', rec.id)])
            rec.mreq_count = self.env['construction.material.requisition'].search_count([('project_id', '=', rec.id)])
            rec.task_count = self.env['construction.task'].search_count([('project_id', '=', rec.id)])
            rec.phase_count = self.env['construction.phase'].search_count([('project_id', '=', rec.id)])
            rec.expense_count = self.env['construction.extra.expense'].search_count([('project_id', '=', rec.id)])

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})

    def action_short_close(self):
        self.write({'state': 'short_closed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_sub_projects(self):
        return {
            'name': _('Sub Projects'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.sub.project',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_budgets(self):
        return {
            'name': _('Budgets'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.budget',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_work_orders(self):
        return {
            'name': _('Work Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.work.order',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_mreq(self):
        return {
            'name': _('Material Requisitions'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.material.requisition',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_tasks(self):
        return {
            'name': _('Tasks'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.task',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_phases(self):
        return {
            'name': _('Phases (WBS)'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.phase',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_expenses(self):
        return {
            'name': _('Extra Expenses'),
            'type': 'ir.actions.act_window',
            'res_model': 'construction.extra.expense',
            'view_mode': 'list,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(_('End Date must be after Start Date.'))


class ConstructionProjectImage(models.Model):
    _name = 'construction.project.image'
    _description = 'Construction Project Image'

    project_id = fields.Many2one('construction.project', string='Project', ondelete='cascade')
    name = fields.Char(string='Description')
    image = fields.Binary(string='Image', attachment=True)


class ConstructionPermit(models.Model):
    _name = 'construction.permit'
    _description = 'Construction Permit & Approval'

    project_id = fields.Many2one('construction.project', string='Project', ondelete='cascade')
    name = fields.Char(string='Permit Name', required=True)
    permit_type = fields.Selection([
        ('building', 'Building Permit'),
        ('environmental', 'Environmental Clearance'),
        ('fire', 'Fire Safety'),
        ('electrical', 'Electrical'),
        ('plumbing', 'Plumbing'),
        ('other', 'Other'),
    ], string='Type', default='building')
    issue_date = fields.Date(string='Issue Date')
    expiry_date = fields.Date(string='Expiry Date')
    issuing_authority = fields.Char(string='Issuing Authority')
    document = fields.Binary(string='Document', attachment=True)
    document_name = fields.Char(string='File Name')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending')
    notes = fields.Text(string='Notes')
