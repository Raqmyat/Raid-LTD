import logging

from markupsafe import Markup

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

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
# who is notified when a record reaches a status ('cancel' = refused)
NOTIFY_ROLE = {
    'submitted': R_OPS, 'ops_approved': R_HR, 'hr_approved': R_HR,
    'finance': R_FIN, 'ceo': R_CEO, 'cancel': R_SUBMIT,
}

# The approval buttons (same everywhere: payslip form, payslip list, pay run form)
# key -> {status the button applies to: (required role, single-record method)}
BULK = {
    'submit': {'draft': (R_SUBMIT, 'action_approval_submit')},
    # separate buttons per role (Approve Ops / Approve HR)
    'approve_ops': {'submitted': (R_OPS, 'action_approval_ops_approve')},
    'approve_hr': {'ops_approved': (R_HR, 'action_approval_hr_approve')},
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
}
# (key, label, css class) in display order
BUTTONS = [
    ('submit', 'Submit', 'btn-primary'),
    ('approve_ops', 'Approve Ops', 'btn-primary'),
    ('approve_hr', 'Approve HR', 'btn-primary'),
    ('send_finance', 'Send to Finance', 'btn-primary'),
    ('send_ceo', 'Send to CEO', 'btn-primary'),
    ('close', 'Close & Post', 'btn-success'),
    ('refuse', 'Refuse', 'btn-danger'),
]
BUTTON_LABELS = {key: label for key, label, _css in BUTTONS}


class ApprovalMixin(models.AbstractModel):
    """Approval cycle that runs on an EXISTING status field of the model
    (`_approval_field`); the mixin adds no field of its own."""
    _name = 'approval.mixin'
    _description = 'Approval Workflow Mixin'

    _approval_field = 'approval_state'
    # methods that are applied to the whole set of records at once in bulk mode
    _approval_batch_methods = ('action_approval_close',)

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

    def _search_approval_my_turn(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_("Unsupported operator on My Turn."))
        positive = (operator == '=') == bool(value)
        return [(self._approval_field, 'in' if positive else 'not in', self._approval_user_states())]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _approval_cur(self):
        self.ensure_one()
        return self[self._approval_field]

    def _approval_label(self, state):
        return dict(self._fields[self._approval_field]._description_selection(self.env)).get(state, state)

    def _approval_guarded_values(self):
        """Values of the status field that can only be set by the approval buttons
        (None = every value)."""
        return None

    def _approval_check_write(self, vals):
        field = self._approval_field
        if field in vals and not self.env.context.get('approval_internal'):
            guarded = self._approval_guarded_values()
            if guarded is None or vals[field] in guarded:
                raise UserError(_("The approval status can only be changed through the approval buttons."))

    def _approval_set(self, state):
        # the role is checked explicitly before; sudo lets approvers who do not
        # have write access on the record move the status
        self.sudo().with_context(approval_internal=True).write({self._approval_field: state})
        self._approval_notify()

    def _approval_lock(self):
        """Lock the rows and re-read the status from the database, so that two
        simultaneous clicks (double click / two approvers) cannot both act on the
        same status: the second one waits, then sees the new status."""
        if not self.ids:
            return
        self.env.cr.execute(
            'SELECT id FROM "%s" WHERE id IN %%s FOR UPDATE' % self._table, (tuple(self.ids),))
        self.invalidate_recordset([self._approval_field])

    def _approval_check_transition(self, key):
        """Hook: extra checks before a transition (raise UserError)."""

    # ------------------------------------------------------------------
    # single-record transitions (strict: raise on wrong status / role)
    # ------------------------------------------------------------------
    def _approval_transition(self, key):
        from_states, to_state, role = TRANSITIONS[key]
        self._approval_check_role(role)
        for rec in self:
            if rec._approval_cur() not in from_states:
                raise UserError(_(
                    "%(name)s is in status '%(state)s' and cannot be moved to '%(to)s'.",
                    name=rec.display_name,
                    state=rec._approval_label(rec._approval_cur()),
                    to=rec._approval_label(to_state)))
        self._approval_check_transition(key)
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
            role = CLOSE_ROLES.get(rec._approval_cur())
            if not role:
                raise UserError(_(
                    "%(name)s (status '%(state)s') is not ready to be closed.",
                    name=rec.display_name, state=rec._approval_label(rec._approval_cur())))
            rec._approval_check_role(role)
        self._approval_finish()

    def action_approval_refuse(self):
        for rec in self:
            cur = rec._approval_cur()
            role = STATE_ACTOR.get(cur)
            if not role or cur == 'draft':
                raise UserError(_(
                    "%(name)s (status '%(state)s') cannot be refused.",
                    name=rec.display_name, state=rec._approval_label(cur)))
            rec._approval_check_role(role)
        self._approval_refuse()

    # hooks (overridden by the concrete models)
    def _approval_finish(self):
        self._approval_set('done')

    def _approval_refuse(self):
        self._approval_set('refused')

    # ------------------------------------------------------------------
    # bulk processing: applies a button to a mixed set of records
    # ------------------------------------------------------------------
    def _approval_bulk(self, key, expected=None):
        """expected: the status the user saw when pressing the button. Either a
        status (str) for all records, or {record_id: status}. A record that is no
        longer in that status (somebody already moved it, or the button was
        pressed twice) is skipped instead of being pushed one more step."""
        rules = BULK[key]
        done = self.browse()
        skipped_status = skipped_role = skipped_moved = 0
        failed = []
        self._approval_lock()
        groups = {}  # method -> records (in order)
        for rec in self:
            exp = expected.get(rec.id) if isinstance(expected, dict) else expected
            if exp and rec._approval_cur() != exp:
                skipped_moved += 1
                continue
            rule = rules.get(rec._approval_cur())
            if not rule:
                skipped_status += 1
                continue
            role, method = rule
            if not self._approval_user_can(role):
                skipped_role += 1
                continue
            groups[method] = groups.get(method, self.browse()) | rec
        for method, recs in groups.items():
            if method in self._approval_batch_methods and len(recs) > 1:
                # one call for the whole set (e.g. one journal entry for all of them)
                try:
                    with self.env.cr.savepoint():
                        getattr(recs.with_context(approval_no_notify=True), method)()
                    done |= recs
                    continue
                except UserError:
                    pass  # find out which record is the problem, one by one
            for rec in recs:
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
        if skipped_moved:
            lines.append(_("%(n)s skipped (already processed by someone else).", n=skipped_moved))
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
        cur = self._approval_cur()
        return {
            'record_id': self.id,
            'name': self.display_name,
            'extra': '',
            'state': cur,
            'state_label': self._approval_label(cur),
        }

    def _approval_open_wizard(self, key):
        rules = BULK[key]
        lines = []
        for rec in self:
            rule = rules.get(rec._approval_cur())
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
            cur = rec._approval_cur()
            by_state.setdefault(cur, self.browse())
            by_state[cur] |= rec
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
                if state in ('cancel', 'refused'):
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


def _make_direct(key, state=None):
    def method(self):
        return self._approval_bulk(key, expected=state)
    return method


def _make_wizard(key):
    def method(self):
        return self._approval_open_wizard(key)
    return method


# action_btn_<key>    : direct (payslip form)
# action_wizard_<key> : opens the "who do you want to approve" wizard (list / pay run)
for _key in BULK:
    setattr(ApprovalMixin, 'action_btn_%s' % _key, _make_direct(_key))
    # one button per (action, status): the status the user saw is checked on the server
    for _state in BULK[_key]:
        setattr(ApprovalMixin, 'action_btn_%s__%s' % (_key, _state), _make_direct(_key, _state))
    setattr(ApprovalMixin, 'action_wizard_%s' % _key, _make_wizard(_key))
