from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import UserError


class HrAuditReportWizard(models.TransientModel):
    _name = 'hr.audit.report.wizard'
    _description = 'Weekly Tasks Report Wizard'

    date_from = fields.Date(string='From', required=True,
                            default=lambda s: fields.Date.context_today(s) - timedelta(days=6))
    date_to = fields.Date(string='To', required=True, default=fields.Date.context_today)
    user_ids = fields.Many2many('res.users', string='Users (empty = all)')
    res_model = fields.Selection([
        ('all', 'All'), ('hr.employee', 'Employee files'), ('hr.leave', 'Time Off'),
        ('hr.leave.allocation', 'Allocations'), ('hr.attendance', 'Attendance'),
        ('hr.payslip', 'Payslips'),
    ], string='Module', default='all', required=True)
    action_type = fields.Selection([
        ('all', 'All'), ('create', 'Created'), ('write', 'Updated'), ('unlink', 'Deleted'),
    ], string='Action', default='all', required=True)

    def action_open_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_('"From" date must be before "To" date.'))
        domain = [('log_day', '>=', self.date_from), ('log_day', '<=', self.date_to)]
        if self.user_ids:
            domain.append(('user_id', 'in', self.user_ids.ids))
        if self.res_model != 'all':
            domain.append(('res_model', '=', self.res_model))
        if self.action_type != 'all':
            domain.append(('action', '=', self.action_type))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tasks Report: %s → %s') % (self.date_from, self.date_to),
            'res_model': 'hr.audit.log',
            'views': [(False, 'list'), (False, 'pivot'), (False, 'form')],
            'domain': domain,
            'context': {'search_default_group_user': 1, 'search_default_group_model': 1, 'create': False},
        }
