import logging

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .view_patch import STATES, patch_header, patch_list_column, patch_search

_logger = logging.getLogger(__name__)

MODULE = 'hr_leave_approval'
G_MANAGER = '%s.group_leave_manager' % MODULE
G_HR = '%s.group_leave_hr' % MODULE
G_CFO = '%s.group_leave_cfo' % MODULE
G_CEO = '%s.group_leave_ceo' % MODULE
ROLE_GROUP = {'hr': G_HR, 'cfo': G_CFO, 'ceo': G_CEO}

PENDING = ('manager', 'hr', 'cfo', 'ceo')
# who has to act on a status ('manager' = the employee's direct manager, not a group)
STATE_ROLE = {'manager': 'manager', 'hr': 'hr', 'cfo': 'cfo', 'ceo': 'ceo', 'refused': 'hr'}

# button -> {status it applies to: next status}
FLOW = {
    'manager_approve': {'manager': 'hr'},
    'send_cfo': {'hr': 'cfo'},
    'send_ceo': {'cfo': 'ceo'},
    'close': {'hr': 'done', 'cfo': 'done', 'ceo': 'done'},
    'refuse': {s: 'refused' for s in PENDING},
    'reset': {'refused': 'reset'},
}
# (key, label, css class, groups that see the button in the LIST header)
BUTTONS = [
    ('manager_approve', 'Approve', 'btn-primary', [G_MANAGER]),
    ('close', 'Approve & Close', 'btn-success', [G_HR, G_CFO, G_CEO]),
    ('send_cfo', 'Send to CFO', 'btn-primary', [G_HR]),
    ('send_ceo', 'Send to CEO', 'btn-primary', [G_CFO]),
    ('refuse', 'Refuse', 'btn-danger', [G_MANAGER]),
    ('reset', 'Reset Approval', 'btn-secondary', [G_HR]),
]
BUTTON_LABELS = {k: l for k, l, _c, _g in BUTTONS}
# Form button visibility (needs leave_can_act = the current user may act on this record now)
FORM_INVISIBLE = {
    'manager_approve': "not leave_can_act or leave_approval_state != 'manager'",
    'close': "not leave_can_act or leave_approval_state not in ['hr', 'cfo', 'ceo']",
    'send_cfo': "not leave_can_act or leave_approval_state != 'hr'",
    'send_ceo': "not leave_can_act or leave_approval_state != 'cfo'",
    'refuse': "not leave_can_act or leave_approval_state not in ['manager', 'hr', 'cfo', 'ceo']",
    'reset': "not leave_can_act or leave_approval_state != 'refused'",
}

# standard buttons of the old cycle (removed). Extra names: system parameter
# hr_leave_approval.hide_buttons (comma separated; restart / upgrade to refresh the view cache)
HIDE_NAMES = {'action_approve', 'action_validate', 'action_refuse'}
HIDE_LABELS = {'approve', 'validate', 'refuse'}


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    leave_approval_state = fields.Selection(
        STATES, string='Approval Status', default='manager', required=True,
        tracking=True, index=True, copy=False)
    leave_approval_manager_id = fields.Many2one(
        'res.users', string='Approval Manager', compute='_compute_lv_manager',
        store=True, index=True)
    leave_can_act = fields.Boolean(compute='_compute_lv_can_act')
    leave_approval_my_turn = fields.Boolean(
        string='My Turn', compute='_compute_lv_my_turn', search='_search_lv_my_turn')

    # ------------------------------------------------------------------
    # who is the manager / who may act
    # ------------------------------------------------------------------
    @api.depends('employee_id.parent_id.user_id', 'employee_id.leave_manager_id')
    def _compute_lv_manager(self):
        for leave in self:
            emp = leave.employee_id
            manager = emp.leave_manager_id if 'leave_manager_id' in emp._fields else False
            leave.leave_approval_manager_id = manager or emp.parent_id.user_id

    def _lv_allow_self(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'hr_leave_approval.allow_self_approval', 'False') in ('True', '1')

    def _lv_user_can_act(self):
        """May the current user act on this request in its current status?"""
        self.ensure_one()
        user = self.env.user
        role = STATE_ROLE.get(self.leave_approval_state)
        if not role:
            return False
        if user.has_group('base.group_system'):
            return True
        if self.employee_id.user_id == user and not self._lv_allow_self():
            return False  # nobody approves his own request
        if role == 'manager':
            return self.leave_approval_manager_id == user
        return user.has_group(ROLE_GROUP[role])

    @api.depends_context('uid')
    @api.depends('leave_approval_state', 'employee_id', 'leave_approval_manager_id')
    def _compute_lv_can_act(self):
        for leave in self:
            leave.leave_can_act = leave._lv_user_can_act()

    @api.depends_context('uid')
    @api.depends('leave_approval_state', 'employee_id', 'leave_approval_manager_id')
    def _compute_lv_my_turn(self):
        for leave in self:
            leave.leave_approval_my_turn = (
                leave.leave_approval_state in PENDING and leave._lv_user_can_act())

    def _search_lv_my_turn(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_("Unsupported operator on My Turn."))
        positive = (operator == '=') == bool(value)
        user = self.env.user
        if user.has_group('base.group_system'):
            domain = [('leave_approval_state', 'in', list(PENDING))]
        else:
            clauses = [['&', ('leave_approval_state', '=', 'manager'),
                        ('leave_approval_manager_id', '=', user.id)]]
            for role, state in (('hr', 'hr'), ('cfo', 'cfo'), ('ceo', 'ceo')):
                if user.has_group(ROLE_GROUP[role]):
                    clauses.append([('leave_approval_state', '=', state)])
            domain = ['|'] * (len(clauses) - 1)
            for clause in clauses:
                domain += clause
            if not self._lv_allow_self():
                domain = ['&'] + domain + [('employee_id.user_id', '!=', user.id)]
        if positive:
            return domain
        return [('id', 'not in', self.sudo().search(domain).ids)]

    # ------------------------------------------------------------------
    # views
    # ------------------------------------------------------------------
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'search':
            patch_search(arch)
        elif view_type in ('list', 'form'):
            extra = self.env['ir.config_parameter'].sudo().get_param(
                'hr_leave_approval.hide_buttons', '')
            names = HIDE_NAMES | {n.strip() for n in extra.split(',') if n.strip()}
            if view_type == 'form':
                # full forms only (with a header), never the small create dialogs
                if arch.xpath('./header'):
                    specs = [{'name': 'action_lvbtn_%s' % key, 'string': _(label), 'class': css,
                              'invisible': FORM_INVISIBLE[key]}
                             for key, label, css, _groups in BUTTONS]
                    patch_header(arch, specs, names, HIDE_LABELS, statusbar=True,
                                 create_header=False)
            else:
                specs = [{'name': 'action_lvwiz_%s' % key, 'string': _(label), 'class': css,
                          'groups': ','.join(groups + ['base.group_system'])}
                         for key, label, css, groups in BUTTONS]
                patch_header(arch, specs, names, HIDE_LABELS)
                patch_list_column(arch)
        return arch, view

    # ------------------------------------------------------------------
    # the approval status follows the request
    # ------------------------------------------------------------------
    def _lv_exempt(self):
        """Leave types with 'No validation' never enter the cycle."""
        return self.filtered(lambda l: getattr(l, 'validation_type', False) == 'no_validation')

    def _lv_initial_state(self):
        self.ensure_one()
        if self.env.context.get('lv_closing') or self._lv_exempt() or self.state == 'validate':
            return 'done'
        if self.state in ('refuse', 'cancel'):
            return 'refused'
        if self.state == 'draft':
            return 'draft'
        manager = self.leave_approval_manager_id
        if not manager or manager == self.employee_id.user_id:
            return 'hr'  # no manager above the employee: straight to HR
        return 'manager'

    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        silent = leaves.sudo().with_context(lv_internal=True, tracking_disable=True)
        for leave in silent:
            target = leave._lv_initial_state()
            leave.write({'leave_approval_state': target})
            if target == 'hr' and leave.state not in ('validate', 'refuse', 'cancel', 'draft'):
                leave.message_post(body=_("No direct manager above the employee: sent straight to HR."))
        leaves.filtered(lambda l: l.leave_approval_state in PENDING)._lv_notify()
        return leaves

    def write(self, vals):
        if 'leave_approval_state' in vals and not self.env.context.get('lv_internal'):
            raise UserError(_("The approval status can only be changed through the approval buttons."))
        res = super().write(vals)
        new_state = vals.get('state')
        if new_state and not self.env.context.get('lv_closing'):
            if new_state in ('refuse', 'cancel'):
                for leave in self.filtered(lambda l: l.leave_approval_state not in ('done', 'refused')):
                    leave._lv_set('refused')
            elif new_state == 'draft':
                for leave in self.filtered(lambda l: l.leave_approval_state != 'draft'):
                    leave._lv_set('draft')
            elif new_state == 'confirm':
                for leave in self.filtered(lambda l: l.leave_approval_state in ('draft', 'refused')):
                    leave._lv_set(leave._lv_initial_state())
        return res

    def _lv_set(self, state):
        self.sudo().with_context(lv_internal=True).write({'leave_approval_state': state})
        self._lv_notify()

    # ------------------------------------------------------------------
    # applying a button on ONE request (strict) / on a mixed set (bulk)
    # ------------------------------------------------------------------
    def _lv_apply(self, key):
        self.ensure_one()
        target = FLOW[key].get(self.leave_approval_state)
        if not target:
            raise UserError(_("%(name)s is in status '%(state)s': '%(button)s' does not apply.",
                              name=self.display_name,
                              state=self._lv_label(self.leave_approval_state),
                              button=_(BUTTON_LABELS[key])))
        if not self._lv_user_can_act():
            raise UserError(_("You are not allowed to act on %s at this step.", self.display_name))
        if key == 'close':
            self._lv_do_close()
        elif key == 'refuse':
            self._lv_do_refuse()
        elif key == 'reset':
            self._lv_do_reset()
            target = self._lv_initial_state()
        self._lv_set(target)

    def _lv_label(self, state):
        return dict(self._fields['leave_approval_state']._description_selection(self.env))[state]

    def _lv_bulk(self, key):
        flow = FLOW[key]
        done = self.browse()
        skipped_status = skipped_role = 0
        failed = []
        for leave in self.sudo():  # permissions are checked by the approval rules, not by Time Off ACLs
            if leave.leave_approval_state not in flow:
                skipped_status += 1
                continue
            if not leave._lv_user_can_act():
                skipped_role += 1
                continue
            try:
                with self.env.cr.savepoint():
                    leave.with_context(lv_no_notify=True)._lv_apply(key)
                done |= leave
            except UserError as e:
                failed.append("%s: %s" % (leave.display_name, e.args[0] if e.args else e))
        done._lv_notify()
        lines = [_("%(n)s request(s) processed.", n=len(done))]
        if skipped_status:
            lines.append(_("%(n)s skipped (not in a status this button applies to).", n=skipped_status))
        if skipped_role:
            lines.append(_("%(n)s skipped (not your approval step).", n=skipped_role))
        if failed:
            lines.append(_("%(n)s failed:", n=len(failed)))
            lines.extend(failed[:10])
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if done and not failed else 'warning',
                'title': _("Time Off Approval"),
                'message': "\n".join(lines),
                'sticky': bool(failed),
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    # ------------------------------------------------------------------
    # wizard: "who do you want to approve?"
    # ------------------------------------------------------------------
    def _lv_open_wizard(self, key):
        flow = FLOW[key]
        lines = []
        for leave in self.sudo():
            if leave.leave_approval_state in flow and leave._lv_user_can_act():
                d_from = fields.Date.to_date(leave.date_from)
                d_to = fields.Date.to_date(leave.date_to)
                lines.append((0, 0, {
                    'record_id': leave.id,
                    'name': leave.employee_id.name or leave.display_name,
                    'extra': '%s  |  %s → %s  |  %g day(s)' % (
                        leave.holiday_status_id.name or '', d_from or '', d_to or '',
                        leave.number_of_days or 0.0),
                    'state_label': leave._lv_label(leave.leave_approval_state),
                }))
        label = _(BUTTON_LABELS[key])
        if not lines:
            raise UserError(_("Nothing is waiting for your action on \"%s\".", label))
        wizard = self.env['hr.leave.approval.wizard'].create({'action_key': key, 'line_ids': lines})
        return {
            'type': 'ir.actions.act_window',
            'name': label,
            'res_model': 'hr.leave.approval.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.model
    def _lv_menu_action(self, key):
        """Menu entry: every request waiting for this button, no selection needed."""
        leaves = self.sudo().search([('leave_approval_state', 'in', list(FLOW[key]))])
        return leaves._lv_open_wizard(key)

    # ------------------------------------------------------------------
    # notifications
    # ------------------------------------------------------------------
    def _lv_recipients(self, state):
        self.ensure_one()
        if state == 'manager':
            return self.leave_approval_manager_id
        if state in ROLE_GROUP:
            group = self.env.ref(ROLE_GROUP[state], raise_if_not_found=False)
            if not group:
                return self.env['res.users']
            group = group.sudo()
            users = group['user_ids'] if 'user_ids' in group._fields else group['users']
            return users.filtered(lambda u: u.active and not u.share)
        if state in ('done', 'refused'):
            return self.employee_id.user_id
        return self.env['res.users']

    def _lv_notify(self):
        if self.env.context.get('lv_no_notify') or not self:
            return
        groups = {}
        for leave in self.sudo():
            state = leave.leave_approval_state
            users = leave._lv_recipients(state) - self.env.user
            if not users:
                continue
            key = (state, tuple(sorted(users.ids)))
            groups.setdefault(key, [users, state, []])[2].append(leave)
        for users, state, leaves in groups.values():
            names = ["%s (%s)" % (l.employee_id.name or l.display_name, l.holiday_status_id.name or '')
                     for l in leaves]
            if state == 'done':
                text = _("%(n)s time off request(s) approved.", n=len(leaves))
            elif state == 'refused':
                text = _("%(n)s time off request(s) refused.", n=len(leaves))
            else:
                text = _("%(n)s time off request(s) are waiting for your approval.", n=len(leaves))
            names_txt = ", ".join(names[:8]) + (" ..." if len(names) > 8 else "")
            try:
                with self.env.cr.savepoint():
                    leaves[0].message_notify(
                        partner_ids=users.partner_id.ids,
                        author_id=self.env.user.partner_id.id,
                        subject=_("Time Off approval"),
                        body=Markup("<p>%s</p><p>%s</p>") % (text, names_txt),
                    )
            except Exception:  # a notification must never block the approval
                _logger.warning("Time off approval notification failed", exc_info=True)

    # ------------------------------------------------------------------
    # closing / refusing / resetting drive the standard request
    # ------------------------------------------------------------------
    def _lv_do_close(self):
        leave = self.sudo().with_context(lv_closing=True)
        if leave.state == 'draft' and hasattr(leave, 'action_confirm'):
            leave.action_confirm()
        if leave.state in ('confirm', 'validate1'):
            leave.action_validate()
        elif leave.state != 'validate':
            raise UserError(_("%s cannot be validated from its current Time Off status.",
                              leave.display_name))

    def _lv_do_refuse(self):
        leave = self.sudo().with_context(lv_closing=True)
        if leave.state in ('confirm', 'validate1', 'validate'):
            leave.action_refuse()

    def _lv_do_reset(self):
        leave = self.sudo().with_context(lv_closing=True)
        if leave.state not in ('refuse', 'cancel'):
            return
        if hasattr(leave, 'action_reset_confirm'):
            leave.action_reset_confirm()
        else:
            if hasattr(leave, 'action_draft'):
                leave.action_draft()
            if hasattr(leave, 'action_confirm'):
                leave.action_confirm()
        if leave.state not in ('draft', 'confirm'):
            raise UserError(_(
                "%s could not be reset to 'To Approve'. Reset it from the standard "
                "Time Off screen first.", leave.display_name))

    # ------------------------------------------------------------------
    # block the standard approval until the cycle is finished
    # ------------------------------------------------------------------
    def _lv_enforce_check(self):
        if self.env.context.get('lv_closing'):
            return
        enforce = self.env['ir.config_parameter'].sudo().get_param('hr_leave_approval.enforce', 'True')
        if enforce in ('False', '0'):
            return
        pending = (self - self._lv_exempt()).filtered(lambda l: l.leave_approval_state != 'done')
        if pending:
            raise UserError(_(
                "These time off requests must go through the approval cycle:\n%s",
                '\n'.join(pending.mapped('display_name'))))

    def action_approve(self, *args, **kwargs):
        self._lv_enforce_check()
        return super().action_approve(*args, **kwargs)

    def action_validate(self, *args, **kwargs):
        self._lv_enforce_check()
        return super().action_validate(*args, **kwargs)


def _make_direct(key):
    def method(self):
        return self._lv_bulk(key)
    return method


def _make_wizard(key):
    def method(self):
        return self._lv_open_wizard(key)
    return method


# action_lvbtn_<key> : direct (form)   |   action_lvwiz_<key> : wizard (list)
for _key, _label, _css, _groups in BUTTONS:
    setattr(HrLeave, 'action_lvbtn_%s' % _key, _make_direct(_key))
    setattr(HrLeave, 'action_lvwiz_%s' % _key, _make_wizard(_key))
