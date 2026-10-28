import logging

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

APPROVAL_STATES = [
    ('draft', 'Draft'),
    ('submitted', 'Submitted'),
    ('ops_approved', 'Operations Approved'),
    ('hr_approved', 'HR Approved'),
    ('finance', 'Finance'),
    ('ceo', 'CEO'),
    ('done', 'Done'),
    ('refused', 'Refused'),
]
APPROVAL_SEQUENCE = {code: idx for idx, (code, _label) in enumerate(APPROVAL_STATES)}
FINAL_STATES = ('done', 'refused')

# Roles (the group behind each role is configurable: approval.step)
R_SUBMIT, R_OPS, R_HR, R_FIN, R_CEO = 'submit', 'ops', 'hr', 'finance', 'ceo'

# key -> (allowed from states, target state, required role)
TRANSITIONS = {
    'submit': (('draft',), 'submitted', R_SUBMIT),
    'ops_approve': (('submitted',), 'ops_approved', R_OPS),
    'hr_approve': (('ops_approved',), 'hr_approved', R_HR),
    'send_finance': (('hr_approved',), 'finance', R_HR),
    'send_ceo': (('finance',), 'ceo', R_FIN),
}
CLOSE_ROLES = {'hr_approved': R_HR, 'finance': R_FIN, 'ceo': R_CEO}
# who has to act on a given status ("My Turn" filter, refuse)
STATE_ACTOR = {
    'draft': R_SUBMIT, 'submitted': R_OPS, 'ops_approved': R_HR,
    'hr_approved': R_HR, 'finance': R_FIN, 'ceo': R_CEO,
}
# who is notified when a record reaches a status
NOTIFY_ROLE = {
    'submitted': R_OPS, 'ops_approved': R_HR, 'hr_approved': R_HR,
    'finance': R_FIN, 'ceo': R_CEO, 'refused': R_SUBMIT,
}

# The approval buttons (same everywhere: payslip form, payslip list, pay run form)
# key -> {status the button applies to: (required role, single-record method)}
BULK = {
    'submit': {'draft': (R_SUBMIT, 'action_approval_submit')},
    'approve': {
        'submitted': (R_OPS, 'action_approval_ops_approve'),
        'ops_approved': (R_HR, 'action_approval_hr_approve'),
    },
    'send_finance': {'hr_approved': (R_HR, 'action_approval_send_finance')},
    'send_ceo': {'finance': (R_FIN, 'action_approval_send_ceo')},
    'close': {
        'hr_approved': (R_HR, 'action_approval_close'),
        'finance': (R_FIN, 'action_approval_close'),
        'ceo': (R_CEO, 'action_approval_close'),
    },
    'refuse': {
        'submitted': (R_OPS, 'action_approval_refuse'),
        'ops_approved': (R_HR, 'action_approval_refuse'),
        'hr_approved': (R_HR, 'action_approval_refuse'),
        'finance': (R_FIN, 'action_approval_refuse'),
        'ceo': (R_CEO, 'action_approval_refuse'),
    },
    'reset': {'refused': (R_SUBMIT, 'action_approval_reset')},
}
# (key, label, css class) in display order
BUTTONS = [
    ('submit', 'Submit', 'btn-primary'),
    ('approve', 'Approve', 'btn-primary'),
    ('send_finance', 'Send to Finance', 'btn-primary'),
    ('send_ceo', 'Send to CEO', 'btn-primary'),
    ('close', 'Close & Post', 'btn-success'),
    ('refuse', 'Refuse', 'btn-danger'),
    ('reset', 'Reset Approval', 'btn-secondary'),
]
BUTTON_LABELS = {key: label for key, label, _css in BUTTONS}


class ApprovalMixin(models.AbstractModel):
    _name = 'approval.mixin'
    _description = 'Approval Workflow Mixin'

    approval_state = fields.Selection(
        APPROVAL_STATES, string='Approval Status', default='draft',
        required=True, tracking=True, index=True, copy=False)
    approval_seq = fields.Integer(
        string='Approval Step', compute='_compute_approval_seq', store=True, index=True)
    approval_my_turn = fields.Boolean(
        string='My Turn', compute='_compute_approval_my_turn',
        search='_search_approval_my_turn')

    # ------------------------------------------------------------------
    # roles / permissions (groups come from the approval.step configuration)
    # ------------------------------------------------------------------
    @api.model
    def _approval_user_can(self, role):
        user = self.env.user
        if user.has_group('base.group_system'):
            return True
        xmlid = self.env['approval.step']._group_xmlid_for(self._name, role)
        try:
            return bool(xmlid) and user.has_group(xmlid)
        except Exception:  # group removed
            return False

    def _approval_check_role(self, role):
        if not self._approval_user_can(role):
            raise UserError(_("You don't have the permission to perform this action."))

    @api.model
    def _approval_user_states(self):
        return [state for state, role in STATE_ACTOR.items() if self._approval_user_can(role)]

    @api.depends('approval_state')
    def _compute_approval_seq(self):
        for rec in self:
            rec.approval_seq = APPROVAL_SEQUENCE.get(rec.approval_state, 0)

    @api.depends_context('uid')
    @api.depends('approval_state')
    def _compute_approval_my_turn(self):
        states = self._approval_user_states()
        for rec in self:
            rec.approval_my_turn = rec.approval_state in states

    def _search_approval_my_turn(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_("Unsupported operator on My Turn."))
        positive = (operator == '=') == bool(value)
        return [('approval_state', 'in' if positive else 'not in', self._approval_user_states())]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _approval_label(self, state):
        return dict(self._fields['approval_state']._description_selection(self.env))[state]

    def _approval_set(self, state):
        # the role is checked explicitly before; sudo lets approvers who do not
        # have write access on the record move the status
        self.sudo().with_context(approval_internal=True).write({'approval_state': state})
        self._approval_notify()

    def write(self, vals):
        if 'approval_state' in vals and not self.env.context.get('approval_internal'):
            raise UserError(_("The approval status can only be changed through the approval buttons."))
        return super().write(vals)

    def _approval_initial_state(self):
        return 'draft'

    # ------------------------------------------------------------------
    # single-record transitions (strict: raise on wrong status / role)
    # ------------------------------------------------------------------
    def _approval_transition(self, key):
        from_states, to_state, role = TRANSITIONS[key]
        self._approval_check_role(role)
        for rec in self:
            if rec.approval_state not in from_states:
                raise UserError(_(
                    "%(name)s is in status '%(state)s' and cannot be moved to '%(to)s'.",
                    name=rec.display_name,
                    state=rec._approval_label(rec.approval_state),
                    to=rec._approval_label(to_state)))
        self._approval_set(to_state)

    def action_approval_submit(self):
        self._approval_transition('submit')

    def action_approval_ops_approve(self):
        self._approval_transition('ops_approve')

    def action_approval_hr_approve(self):
        self._approval_transition('hr_approve')

    def action_approval_send_finance(self):
        self._approval_transition('send_finance')

    def action_approval_send_ceo(self):
        self._approval_transition('send_ceo')

    def action_approval_close(self):
        for rec in self:
            role = CLOSE_ROLES.get(rec.approval_state)
            if not role:
                raise UserError(_(
                    "%(name)s (status '%(state)s') is not ready to be closed.",
                    name=rec.display_name, state=rec._approval_label(rec.approval_state)))
            rec._approval_check_role(role)
        self._approval_on_done()
        self._approval_set('done')

    def action_approval_refuse(self):
        for rec in self:
            role = STATE_ACTOR.get(rec.approval_state)
            if not role or rec.approval_state == 'draft':
                raise UserError(_(
                    "%(name)s (status '%(state)s') cannot be refused.",
                    name=rec.display_name, state=rec._approval_label(rec.approval_state)))
            rec._approval_check_role(role)
        self._approval_on_refused()
        self._approval_set('refused')

    def action_approval_reset(self):
        self._approval_check_role(R_SUBMIT)
        for rec in self:
            if rec.approval_state != 'refused':
                raise UserError(_("Only refused records can be reset."))
        self._approval_on_reset()
        for rec in self:
            rec._approval_set(rec._approval_initial_state())

    # hooks (overridden by the concrete models)
    def _approval_on_done(self):
        pass

    def _approval_on_refused(self):
        pass

    def _approval_on_reset(self):
        pass

    # ------------------------------------------------------------------
    # bulk processing: applies a button to a mixed set of records
    # ------------------------------------------------------------------
    def _approval_bulk(self, key):
        rules = BULK[key]
        done = self.browse()
        skipped_status = skipped_role = 0
        failed = []
        for rec in self:
            rule = rules.get(rec.approval_state)
            if not rule:
                skipped_status += 1
                continue
            role, method = rule
            if not self._approval_user_can(role):
                skipped_role += 1
                continue
            try:
                with self.env.cr.savepoint():
                    getattr(rec.with_context(approval_no_notify=True), method)()
                done |= rec
            except UserError as e:
                failed.append("%s: %s" % (rec.display_name, e.args[0] if e.args else e))
        done._approval_notify()  # one notification per group, not per record
        lines = [_("%(n)s record(s) processed.", n=len(done))]
        if skipped_status:
            lines.append(_("%(n)s skipped (not in a status this button applies to).", n=skipped_status))
        if skipped_role:
            lines.append(_("%(n)s skipped (not your approval role).", n=skipped_role))
        if failed:
            lines.append(_("%(n)s failed:", n=len(failed)))
            lines.extend(failed[:10])
            if len(failed) > 10:
                lines.append("...")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if done and not failed else 'warning',
                'title': _("Approval"),
                'message': "\n".join(lines),
                'sticky': bool(failed),
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    # ------------------------------------------------------------------
    # wizard: "who do you want to approve?"
    # ------------------------------------------------------------------
    def _approval_wizard_line_vals(self):
        self.ensure_one()
        return {
            'record_id': self.id,
            'name': self.display_name,
            'extra': '',
            'state': self.approval_state,
            'state_label': self._approval_label(self.approval_state),
        }

    def _approval_open_wizard(self, key):
        rules = BULK[key]
        lines = []
        for rec in self:
            rule = rules.get(rec.approval_state)
            if rule and self._approval_user_can(rule[0]):
                lines.append((0, 0, rec._approval_wizard_line_vals()))
        label = _(BUTTON_LABELS[key])
        if not lines:
            raise UserError(_("Nothing is waiting for your action on \"%s\" here.", label))
        wizard = self.env['approval.action.wizard'].create({
            'res_model': self._name,
            'action_key': key,
            'line_ids': lines,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': label,
            'res_model': 'approval.action.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ------------------------------------------------------------------
    # notifications: tell the people who must act now
    # ------------------------------------------------------------------
    def _approval_notify_name(self):
        return self.display_name

    def _approval_notify_targets(self):
        """[(record to post on, records it covers)] - one message per target."""
        return [(rec, rec) for rec in self]

    def _approval_notify(self):
        if self.env.context.get('approval_no_notify') or not self:
            return
        Step = self.env['approval.step']
        by_state = {}
        for rec in self:
            by_state.setdefault(rec.approval_state, self.browse())
            by_state[rec.approval_state] |= rec
        for state, recs in by_state.items():
            role = NOTIFY_ROLE.get(state)
            step = Step._get_step(self._name, role) if role else None
            if not step or not step.notify:
                continue
            users = step._get_users() - self.env.user
            if not users:
                continue
            label = recs[0]._approval_label(state)
            for target, covered in recs._approval_notify_targets():
                if state == 'refused':
                    text = _("%(n)s record(s) were refused / returned.", n=len(covered))
                else:
                    text = _("%(n)s record(s) are waiting for your action (status: %(s)s).",
                             n=len(covered), s=label)
                names = [r._approval_notify_name() for r in covered]
                names_txt = ", ".join(names[:8]) + (" ..." if len(names) > 8 else "")
                try:
                    with self.env.cr.savepoint():
                        target.sudo().message_notify(
                            partner_ids=users.partner_id.ids,
                            author_id=self.env.user.partner_id.id,
                            subject=_("Approval needed: %s", self._description or self._name),
                            body=Markup("<p>%s</p><p>%s</p>") % (text, names_txt),
                        )
                except Exception:  # a notification must never block the approval
                    _logger.warning("Approval notification failed", exc_info=True)


def _make_direct(key):
    def method(self):
        return self._approval_bulk(key)
    return method


def _make_wizard(key):
    def method(self):
        return self._approval_open_wizard(key)
    return method


# action_btn_<key>    : direct (payslip form)
# action_wizard_<key> : opens the "who do you want to approve" wizard (list / pay run)
for _key, _label, _css in BUTTONS:
    setattr(ApprovalMixin, 'action_btn_%s' % _key, _make_direct(_key))
    setattr(ApprovalMixin, 'action_wizard_%s' % _key, _make_wizard(_key))
    # v3 name, kept so views cached by the browser before the upgrade still work
    setattr(ApprovalMixin, 'action_bulk_%s' % _key, _make_wizard(_key))
