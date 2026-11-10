from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# alert stages: months before the end date. One alert per stage, each month.
ALERT_MONTHS = (3, 2, 1)


class CrmCustomerContract(models.Model):
    _name = 'crm.customer.contract'
    _description = 'Customer Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_end asc, id desc'

    name = fields.Char(string='Reference', default=lambda self: _('New'), copy=False, readonly=True, index=True)
    title = fields.Char(string='Contract Subject', tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True, index=True,
        domain="[('parent_id', '=', False)]")
    opportunity_id = fields.Many2one(
        'crm.lead', string='Opportunity', domain="[('partner_id', '=?', partner_id)]", tracking=True)
    user_id = fields.Many2one(
        'res.users', string='Responsible', default=lambda self: self.env.user, tracking=True,
        domain="[('share', '=', False)]")
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='company_id.currency_id', readonly=True)
    amount = fields.Monetary(string='Contract Value', currency_field='currency_id', tracking=True)
    date_start = fields.Date(string='Start Date', required=True, tracking=True,
                             default=fields.Date.context_today)
    date_end = fields.Date(string='End Date', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False, index=True)
    days_left = fields.Integer(string='Days Left', compute='_compute_days_left')
    alert_stage = fields.Integer(
        string='Last Alert (months before end)', default=0, copy=False, readonly=True,
        help='0 = no alert sent yet; otherwise the last stage sent (3, 2 or 1 month before the end date).')
    terms = fields.Html(string='Terms & Details')
    active = fields.Boolean(default=True)

    # ------------------------------------------------------------------
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_end < rec.date_start:
                raise ValidationError(_("The end date cannot be before the start date."))

    @api.depends('date_end', 'state')
    def _compute_days_left(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_left = (rec.date_end - today).days if rec.date_end and rec.state == 'running' else 0

    @api.depends('name', 'partner_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s - %s' % (rec.name, rec.partner_id.name) if rec.partner_id else rec.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('crm.customer.contract') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        if 'date_end' in vals:  # renewed / changed end date: alerts start again
            vals['alert_stage'] = 0
        res = super().write(vals)
        if 'date_end' in vals or vals.get('state') in ('draft', 'expired', 'cancelled'):
            self._clear_alert_activities()
        return res

    # ------------------------------------------------------------------
    # buttons
    # ------------------------------------------------------------------
    def action_confirm(self):
        self.write({'state': 'running'})
        self._send_expiry_alerts()  # a contract that is already near its end alerts at once

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_draft(self):
        self.write({'state': 'draft'})

    # ------------------------------------------------------------------
    # alerts: Activity (To-Do) for every internal user, once per stage
    # ------------------------------------------------------------------
    def _clear_alert_activities(self):
        self.activity_unlink(['crm_customer_contract.mail_activity_type_contract_expiry'])

    def _current_alert_stage(self, today):
        """3, 2 or 1 = the closest stage already reached today; 0 = too early."""
        self.ensure_one()
        stage = 0
        for months in ALERT_MONTHS:  # 3 -> 2 -> 1, the last one reached wins
            if today >= self.date_end - relativedelta(months=months):
                stage = months
        return stage

    def _send_expiry_alerts(self):
        today = fields.Date.context_today(self)
        activity_type = self.env.ref('crm_customer_contract.mail_activity_type_contract_expiry')
        # sudo: the cron/confirm user may not be allowed to schedule for every user
        users = self.env['res.users'].sudo().search([('share', '=', False), ('active', '=', True)])
        for rec in self.filtered(lambda c: c.state == 'running' and c.date_end and c.date_end >= today):
            stage = rec._current_alert_stage(today)
            if not stage or (rec.alert_stage and stage >= rec.alert_stage):
                continue  # too early, or this stage was already sent
            rec._clear_alert_activities()  # the new alert replaces the previous month's one
            summary = _("Contract %(ref)s - %(customer)s ends on %(date)s (%(n)s month(s) left)",
                        ref=rec.name, customer=rec.partner_id.name, date=rec.date_end, n=stage)
            note = _("Customer: %(customer)s | Start: %(start)s | End: %(end)s | Responsible: %(user)s",
                     customer=rec.partner_id.name, start=rec.date_start, end=rec.date_end,
                     user=rec.user_id.name or '-')
            for user in users.filtered(lambda u: rec.company_id in u.company_ids):
                rec.sudo().activity_schedule(
                    act_type_xmlid='crm_customer_contract.mail_activity_type_contract_expiry',
                    date_deadline=rec.date_end, summary=summary, note=note, user_id=user.id)
            rec.alert_stage = stage

    @api.model
    def _cron_contract_expiry(self):
        today = fields.Date.context_today(self)
        # contracts that passed their end date
        expired = self.search([('state', '=', 'running'), ('date_end', '<', today)])
        expired.write({'state': 'expired'})
        # contracts inside the 3-month window
        window = self.search([
            ('state', '=', 'running'),
            ('date_end', '>=', today),
            ('date_end', '<=', today + relativedelta(months=max(ALERT_MONTHS))),
        ])
        window._send_expiry_alerts()
