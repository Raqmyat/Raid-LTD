import logging

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

ALERT_SUMMARY = '⚠ Client contract expiry'
REMINDER_DAYS = (30, 15, 7)          # reminders sent on top of the contract's own notice period
DEFAULT_NOTICE_PARAM = 'crm_client_contract.default_notice_days'


class CrmClientContractService(models.Model):
    _name = 'crm.client.contract.service'
    _description = 'Client Contract Service'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer()


class CrmClientContract(models.Model):
    _name = 'crm.client.contract'
    _description = 'Client Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_end asc, id desc'
    _rec_name = 'name'

    # ------------------------------------------------------------ identification
    name = fields.Char(string='Reference', default='/', copy=False, readonly=True, index=True, tracking=True)
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one(
        'res.partner', string='Client', required=True, index=True, tracking=True,
        domain="[('is_company', '=', True)]",
        help='The client company we manage payroll / HR affairs for.')
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity', index=True, copy=False,
                                     domain="[('type', '=', 'opportunity')]")
    client_company_id = fields.Many2one(
        'res.company', string='Client Company (HR system)', copy=False,
        help='The company that holds this client\'s employees in the HR / payroll system. '
             'Used to compare the contracted headcount with the real one.')
    company_id = fields.Many2one('res.company', string='Our Company', required=True,
                                 default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one('res.users', string='Account Manager', default=lambda self: self.env.user,
                              tracking=True, index=True)
    notify_user_ids = fields.Many2many(
        'res.users', 'crm_client_contract_notify_rel', 'contract_id', 'user_id',
        string='Also Notify', domain="[('share', '=', False)]",
        help='Any internal user who must receive the expiry alerts of this contract '
             '(in addition to the account manager and the followers).')
    contract_type = fields.Selection([
        ('payroll', 'Payroll Outsourcing'),
        ('hr_services', 'HR Administration (Employee Affairs)'),
        ('full_peo', 'Full HR + Payroll (PEO)'),
        ('staffing', 'Manpower Supply / Staffing'),
        ('recruitment', 'Recruitment'),
        ('other', 'Other'),
    ], string='Contract Type', required=True, default='payroll', tracking=True)
    service_ids = fields.Many2many('crm.client.contract.service', string='Services Included')

    # ------------------------------------------------------------ term
    date_signed = fields.Date(string='Signing Date')
    date_start = fields.Date(string='Start Date', required=True, tracking=True, default=fields.Date.context_today)
    date_end = fields.Date(string='End Date', required=True, tracking=True, index=True)
    duration_days = fields.Integer(string='Duration (days)', compute='_compute_duration_days')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('renewed', 'Renewed'),
        ('terminated', 'Terminated'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True, index=True)
    expiry_status = fields.Selection([
        ('na', 'Not Running'),
        ('ok', 'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Expiry Status', compute='_compute_expiry_status', store=True, index=True,
        help='Refreshed every day by the scheduled action.')
    days_left = fields.Integer(string='Days Left', compute='_compute_days_left')
    notice_days = fields.Integer(
        string='Alert Before (days)', default=lambda self: self._default_notice_days(),
        help='Alerts start this many days before the end date, then again at 30 / 15 / 7 days '
             'and when the contract expires.')
    auto_renew = fields.Boolean(
        string='Auto-Renew', tracking=True,
        help='When the end date passes, the next term is created automatically.')
    renewal_months = fields.Integer(string='Renewal Term (months)', default=12)
    termination_notice_days = fields.Integer(
        string='Termination Notice (days)', default=30,
        help='Notice period the client / we must respect to terminate the contract.')
    previous_contract_id = fields.Many2one('crm.client.contract', string='Previous Term', copy=False, readonly=True)
    renewed_contract_id = fields.Many2one('crm.client.contract', string='Renewed By', copy=False, readonly=True)
    last_alert_level = fields.Integer(copy=False, help='Technical: last alert threshold that was sent.')

    # ------------------------------------------------------------ fees / scope
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.company.currency_id)
    fee_type = fields.Selection([
        ('per_employee', 'Per Employee / Month'),
        ('fixed_monthly', 'Fixed Monthly Fee'),
        ('percent_payroll', '% of Payroll'),
        ('one_time', 'One-time Fee'),
    ], string='Fee Type', default='per_employee', required=True)
    fee_amount = fields.Monetary(string='Fee Amount', currency_field='currency_id')
    fee_percent = fields.Float(string='Fee %')
    headcount = fields.Integer(string='Contracted Employees', tracking=True)
    actual_headcount = fields.Integer(string='Actual Employees', compute='_compute_actual_headcount')
    monthly_value = fields.Monetary(
        string='Estimated Monthly Fees', compute='_compute_monthly_value', store=True,
        currency_field='currency_id',
        help='Per employee: fee x contracted employees. Fixed: the fee. Not computed for % / one-time fees.')
    payroll_cycle = fields.Selection([
        ('monthly', 'Monthly'), ('bi_weekly', 'Bi-weekly'), ('weekly', 'Weekly'),
    ], string='Payroll Cycle', default='monthly')
    payroll_cutoff_day = fields.Integer(string='Attendance Cut-off Day', help='Day of the month the client closes attendance / changes.')
    payday = fields.Integer(string='Salary Payment Day', help='Day of the month salaries must be paid.')
    payment_days = fields.Integer(string='Invoice Due (days)', default=30)
    notes = fields.Html(string='Terms & Notes')

    # ------------------------------------------------------------ defaults
    @api.model
    def _default_notice_days(self):
        try:
            return int(self.env['ir.config_parameter'].sudo().get_param(DEFAULT_NOTICE_PARAM, 60))
        except ValueError:
            return 60

    # ------------------------------------------------------------ constraints
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(_('The end date cannot be before the start date.'))

    @api.constrains('payday', 'payroll_cutoff_day')
    def _check_days(self):
        for rec in self:
            for value in (rec.payday, rec.payroll_cutoff_day):
                if value and not 1 <= value <= 31:
                    raise ValidationError(_('Days of the month must be between 1 and 31.'))

    # ------------------------------------------------------------ computes
    @api.depends('date_start', 'date_end')
    def _compute_duration_days(self):
        for rec in self:
            rec.duration_days = (rec.date_end - rec.date_start).days + 1 if rec.date_start and rec.date_end else 0

    def _get_days_left(self, today=None):
        self.ensure_one()
        today = today or fields.Date.context_today(self)
        return (self.date_end - today).days if self.date_end else 0

    @api.depends_context('uid')
    @api.depends('date_end', 'state')
    def _compute_days_left(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_left = rec._get_days_left(today) if rec.state == 'running' else 0

    def _get_expiry_status(self, today=None):
        self.ensure_one()
        if self.state != 'running' or not self.date_end:
            return 'na'
        left = self._get_days_left(today)
        if left < 0:
            return 'expired'
        if left <= max(self.notice_days, 0):
            return 'expiring'
        return 'ok'

    @api.depends('date_end', 'state', 'notice_days')
    def _compute_expiry_status(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.expiry_status = rec._get_expiry_status(today)

    @api.depends('fee_type', 'fee_amount', 'headcount')
    def _compute_monthly_value(self):
        for rec in self:
            if rec.fee_type == 'per_employee':
                rec.monthly_value = rec.fee_amount * rec.headcount
            elif rec.fee_type == 'fixed_monthly':
                rec.monthly_value = rec.fee_amount
            else:
                rec.monthly_value = 0.0

    @api.depends('client_company_id')
    def _compute_actual_headcount(self):
        Employee = self.env['hr.employee'].sudo()
        counts = {}
        companies = self.client_company_id
        if companies:
            for company, count in Employee._read_group([('company_id', 'in', companies.ids)],
                                                       ['company_id'], ['__count']):
                counts[company.id] = count
        for rec in self:
            rec.actual_headcount = counts.get(rec.client_company_id.id, 0)

    # ------------------------------------------------------------ CRUD
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('crm.client.contract') or '/'
        return super().create(vals_list)

    def write(self, vals):
        # a new end date / notice period / status restarts the alert sequence
        if {'date_end', 'notice_days', 'state'} & set(vals) and 'last_alert_level' not in vals:
            vals = dict(vals, last_alert_level=0)
        return super().write(vals)

    @api.depends('name', 'partner_id.name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s - %s' % (rec.name, rec.partner_id.name) if rec.partner_id else rec.name

    # ------------------------------------------------------------ workflow
    def action_confirm(self):
        for rec in self.filtered(lambda r: r.state == 'draft'):
            rec.state = 'running'
        return True

    def action_terminate(self):
        self.filtered(lambda r: r.state == 'running').write({'state': 'terminated'})
        return True

    def action_cancel(self):
        self.filtered(lambda r: r.state in ('draft', 'running')).write({'state': 'cancel'})
        return True

    def action_draft(self):
        self.filtered(lambda r: r.state in ('cancel', 'terminated')).write({'state': 'draft'})
        return True

    def action_open_renew_wizard(self):
        self.ensure_one()
        if self.state != 'running':
            raise UserError(_('Only a running contract can be renewed.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renew Contract'),
            'res_model': 'crm.client.contract.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_contract_id': self.id},
        }

    def _renew(self, date_end, fee_amount=None, headcount=None):
        """Create the next term (running) and close this one (renewed)."""
        self.ensure_one()
        defaults = {
            'date_start': self.date_end + relativedelta(days=1),
            'date_end': date_end,
            'date_signed': fields.Date.context_today(self),
            'previous_contract_id': self.id,
            'state': 'running',
        }
        if fee_amount is not None:
            defaults['fee_amount'] = fee_amount
        if headcount is not None:
            defaults['headcount'] = headcount
        new = self.copy(defaults)
        self.write({'state': 'renewed', 'renewed_contract_id': new.id})
        self.message_post(body=Markup('%s %s') % (_('Renewed by'), new._get_html_link()))
        new.message_post(body=Markup('%s %s') % (_('Renewal of'), self._get_html_link()))
        return new

    def _next_term_end(self):
        self.ensure_one()
        months = self.renewal_months or 12
        return self.date_end + relativedelta(months=months)

    def action_view_chain(self):
        self.ensure_one()
        chain = self
        while chain.previous_contract_id:
            chain = chain.previous_contract_id
        ids = [chain.id]
        while chain.renewed_contract_id:
            chain = chain.renewed_contract_id
            ids.append(chain.id)
        return {
            'type': 'ir.actions.act_window', 'name': _('Contract History'),
            'res_model': 'crm.client.contract', 'view_mode': 'list,form',
            'domain': [('id', 'in', ids)], 'context': {'active_test': False},
        }

    # ------------------------------------------------------------ alerts
    @api.model
    def _alert_thresholds(self, notice_days):
        """Days-left thresholds (descending) at which an alert is sent."""
        if notice_days <= 0:
            return []
        return sorted({notice_days} | {d for d in REMINDER_DAYS if d < notice_days}, reverse=True)

    def _alert_level(self, today=None):
        """-1 expired, N = the smallest threshold reached, 0 = nothing to send yet."""
        self.ensure_one()
        left = self._get_days_left(today)
        if left < 0:
            return -1
        reached = [t for t in self._alert_thresholds(self.notice_days) if left <= t]
        return min(reached) if reached else 0

    def _alert_recipients(self):
        self.ensure_one()
        users = self.user_id | self.notify_user_ids
        followers = self.message_partner_ids.user_ids.filtered(lambda u: not u.share)
        return (users | followers).filtered('active')

    def _send_expiry_alert(self, level):
        self.ensure_one()
        recipients = self._alert_recipients()
        if not recipients:
            return
        left = self._get_days_left()
        if level == -1:
            subject = _('Contract EXPIRED: %s', self.display_name)
            text = _('The contract ended on %(date)s (%(n)s days ago) and was not renewed.',
                     date=self.date_end, n=abs(left))
        else:
            subject = _('Contract expiring in %(n)s day(s): %(name)s', n=left, name=self.display_name)
            text = _('The contract ends on %(date)s (%(n)s day(s) left).', date=self.date_end, n=left)
        body = Markup('<p>%s</p><ul><li>%s: %s</li><li>%s: %s</li><li>%s: %s</li></ul>') % (
            text,
            _('Client'), self.partner_id.display_name,
            _('Type'), dict(self._fields['contract_type']._description_selection(self.env)).get(self.contract_type),
            _('Account Manager'), self.user_id.name or '-')
        try:
            with self.env.cr.savepoint():
                self.message_notify(
                    partner_ids=recipients.partner_id.ids,
                    subject=subject, body=body,
                    author_id=self.env.ref('base.partner_root').id,
                )
        except Exception:  # an alert must never break the cron
            _logger.warning('Contract alert failed for %s', self.display_name, exc_info=True)
        # one open to-do for the account manager (the previous alert to-do is replaced)
        old = self.env['mail.activity'].sudo().search([
            ('res_model', '=', self._name), ('res_id', '=', self.id), ('summary', '=', ALERT_SUMMARY)])
        old.unlink()
        if self.user_id:
            try:
                with self.env.cr.savepoint():
                    self.activity_schedule(
                        'mail.mail_activity_data_todo', date_deadline=max(self.date_end, fields.Date.context_today(self)),
                        summary=ALERT_SUMMARY, note=text, user_id=self.user_id.id)
            except Exception:
                _logger.warning('Contract alert activity failed for %s', self.display_name, exc_info=True)

    @api.model
    def _cron_expiry_alerts(self):
        today = fields.Date.context_today(self)
        # 1) auto-renew (a few terms at most, in case the cron did not run for a long time)
        for contract in self.search([('state', '=', 'running'), ('auto_renew', '=', True),
                                     ('date_end', '<', today)]):
            current = contract
            for _i in range(24):
                if current.state != 'running' or current.date_end >= today:
                    break
                try:
                    with self.env.cr.savepoint():
                        current = current._renew(current._next_term_end())
                except Exception:
                    _logger.warning('Auto-renew failed for %s', current.display_name, exc_info=True)
                    break
        # 2) refresh the stored status, 3) alerts
        self.with_context(active_test=False).search([])._compute_expiry_status()
        running = self.search([('state', '=', 'running')])
        for contract in running:
            level = contract._alert_level(today)
            if level and (not contract.last_alert_level or level < contract.last_alert_level):
                contract._send_expiry_alert(level)
                contract.with_context(tracking_disable=True).sudo().write({'last_alert_level': level})
