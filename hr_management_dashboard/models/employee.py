from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Visa expiry itself is the STANDARD field `visa_expire` (Private Information > Work Permit).
    identification_expire = fields.Date(
        string='ID Expiry Date', groups='hr.group_hr_user', tracking=True, index=True,
        help='Expiry date of the Identification No (ID card), next to the ID number on the employee card.')
    rpt_contract_start = fields.Date(
        string='Contract Start (first)', compute='_compute_rpt_contract_dates', store=True,
        groups='hr_management_dashboard.group_hr_reports_user',
        help='Earliest contract start date found on the employee versions.')
    rpt_contract_end = fields.Date(
        string='Contract End (auto-renewed yearly)', compute='_compute_rpt_contract_dates',
        store=True, index=True, groups='hr_management_dashboard.group_hr_reports_user',
        help='Next anniversary of the contract start date. The contract renews automatically '
             'every year while the employee file is open (active / not departed); the end date '
             'typed on the contract is ignored.')
    rpt_contract_days_left = fields.Integer(
        string='Contract Days Left', compute='_compute_rpt_days_left', groups='hr_management_dashboard.group_hr_reports_user')
    rpt_visa_days_left = fields.Integer(
        string='Visa Days Left', compute='_compute_rpt_days_left', groups='hr.group_hr_user')
    rpt_id_days_left = fields.Integer(
        string='ID Days Left', compute='_compute_rpt_days_left', groups='hr.group_hr_user')

    @staticmethod
    def _rpt_next_anniversary(start, today):
        """Smallest start + N years (N >= 1) that is not in the past."""
        years = max(today.year - start.year, 1)
        end = start + relativedelta(years=years)
        while end < today:
            years += 1
            end = start + relativedelta(years=years)
        return end

    def _rpt_contract_values(self):
        """Single source of truth for the stored dates (used by compute and cron)."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        starts = [d for d in self.version_ids.mapped('contract_date_start') if d]
        start = min(starts) if starts else False
        departed = ('departure_date' in self._fields and self.departure_date
                    and self.departure_date <= today)
        end = False
        if start and self.active and not departed:
            end = self._rpt_next_anniversary(start, today)
        return {'rpt_contract_start': start, 'rpt_contract_end': end}

    @api.depends('version_ids.contract_date_start', 'active')
    def _compute_rpt_contract_dates(self):
        for emp in self:
            vals = emp._rpt_contract_values()
            emp.rpt_contract_start = vals['rpt_contract_start']
            emp.rpt_contract_end = vals['rpt_contract_end']

    @api.depends('rpt_contract_end', 'visa_expire', 'identification_expire')
    def _compute_rpt_days_left(self):
        today = fields.Date.context_today(self)
        for emp in self:
            emp.rpt_id_days_left = (emp.identification_expire - today).days if emp.identification_expire else 0
            emp.rpt_contract_days_left = (emp.rpt_contract_end - today).days if emp.rpt_contract_end else 0
            emp.rpt_visa_days_left = (emp.visa_expire - today).days if emp.visa_expire else 0

    @api.model
    def _cron_refresh_rpt_contract_dates(self):
        """Daily: the auto-renewed end date moves on every anniversary, so a stored value goes stale."""
        employees = self.sudo().with_context(active_test=False, tracking_disable=True).search(
            ['|', ('active', '=', True), ('rpt_contract_end', '!=', False)])
        for emp in employees:
            vals = emp._rpt_contract_values()
            if any(emp[k] != v for k, v in vals.items()):
                emp.write(vals)
