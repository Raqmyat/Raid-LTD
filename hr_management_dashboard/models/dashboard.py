from datetime import datetime, timedelta

import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class HrMgmtDashboard(models.AbstractModel):
    _name = 'hr.mgmt.dashboard'
    _description = 'HR Management Dashboard Data'

    def _check_manager(self):
        if not self.env.user.has_group('hr.group_hr_manager'):
            raise AccessError(_('Only HR managers can open this dashboard.'))

    # ------------------------------------------------------------ Employee status
    @api.model
    def get_employee_status(self, months=12):
        self._check_manager()
        months = max(1, min(int(months or 12), 36))
        Employee = self.env['hr.employee']          # runs as the user => multi-company rules apply
        total = Employee.search_count([])
        with_permit = Employee.search_count([('identification_id', '!=', False)])

        # Company > Department > count
        companies = {}
        for company, dept, count in Employee._read_group(
                [], ['company_id', 'department_id'], ['__count']):
            c = companies.setdefault(company.id, {
                'id': company.id, 'name': company.display_name or _('No Company'),
                'total': 0, 'departments': [],
                'domain': [('company_id', '=', company.id)],
            })
            c['total'] += count
            c['departments'].append({
                'id': dept.id,
                'name': dept.display_name or _('No Department'),
                'count': count,
                'domain': [('company_id', '=', company.id), ('department_id', '=', dept.id or False)],
            })
        company_list = sorted(companies.values(), key=lambda c: c['name'])
        for c in company_list:
            c['departments'].sort(key=lambda d: d['name'])

        # New employees per month (by system creation date, user timezone)
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        now_local = datetime.now(pytz.utc).astimezone(tz)
        first = datetime(now_local.year, now_local.month, 1)
        month_rows = []
        for i in range(months - 1, -1, -1):
            start_naive = first - relativedelta(months=i)
            end_naive = start_naive + relativedelta(months=1)
            start = tz.localize(start_naive).astimezone(pytz.utc).replace(tzinfo=None)
            end = tz.localize(end_naive).astimezone(pytz.utc).replace(tzinfo=None)
            domain = [('create_date', '>=', fields.Datetime.to_string(start)),
                      ('create_date', '<', fields.Datetime.to_string(end))]
            month_rows.append({
                'label': start_naive.strftime('%b %Y'),
                'count': Employee.search_count(domain),
                'domain': domain,
            })

        return {
            'total': total,
            'with_permit': with_permit,
            'without_permit': total - with_permit,
            'permit_domain': [('identification_id', '!=', False)],
            'no_permit_domain': [('identification_id', '=', False)],
            'companies': company_list,
            'months': month_rows,
        }

    # ------------------------------------------------------------ Issues & pending
    def _item(self, label, model, domain, count=None, action=None):
        try:
            cnt = count if count is not None else self.env[model].search_count(domain)
        except (KeyError, AccessError):
            return None
        return {'label': label, 'count': cnt, 'model': model, 'domain': domain, 'action': action}

    @api.model
    def get_issues(self):
        self._check_manager()
        days = int(self.env['ir.config_parameter'].sudo().get_param(
            'hr_management_dashboard.overdue_days', 3))
        now = fields.Datetime.now()
        limit = fields.Datetime.to_string(now - timedelta(days=days))
        soon = fields.Datetime.to_string(now + timedelta(days=3))
        today_start = fields.Datetime.to_string(now.replace(hour=0, minute=0, second=0, microsecond=0))
        today = fields.Date.context_today(self)
        pending = ('state', 'in', ['confirm', 'validate1'])

        Issue = self.env['hr.employee.data.issue']
        Issue._rebuild()
        emp_missing = len(Issue._read_group([], ['employee_id'], ['__count']))

        sections = [
            {'title': _('Time Off'), 'items': [
                self._item(_('Requests waiting for approval'), 'hr.leave', [pending]),
                self._item(_('Overdue approvals (older than %s days)') % days, 'hr.leave',
                           [pending, ('create_date', '<', limit)]),
                self._item(_('Waiting approval but starting within 3 days'), 'hr.leave',
                           [pending, ('date_from', '<=', soon)]),
            ]},
            {'title': _('Allocations'), 'items': [
                self._item(_('Allocations waiting for approval'), 'hr.leave.allocation', [pending]),
                self._item(_('Overdue allocations (older than %s days)') % days, 'hr.leave.allocation',
                           [pending, ('create_date', '<', limit)]),
            ]},
            {'title': _('Attendance'), 'items': [
                self._item(_('Check-in without check-out (before today)'), 'hr.attendance',
                           [('check_out', '=', False), ('check_in', '<', today_start)]),
            ]},
            {'title': _('Payroll'), 'items': [
                self._item(_('Draft payslips whose period already ended'), 'hr.payslip',
                           [('state', '=', 'draft'), ('date_to', '<', today)]),
                self._item(_('Payslips waiting for verification'), 'hr.payslip', [('state', '=', 'verify')]),
                self._item(_('Draft batches whose period already ended'), 'hr.payslip.run',
                           [('state', '=', 'draft'), ('date_end', '<', today)]),
            ]},
            {'title': _('Employee Data'), 'items': [
                self._item(_('Employees with missing data'), 'hr.employee', [], count=emp_missing,
                           action='hr_management_dashboard.action_employee_data_issue_server'),
            ]},
        ]
        for s in sections:
            s['items'] = [i for i in s['items'] if i]
        return {'sections': [s for s in sections if s['items']], 'overdue_days': days}
