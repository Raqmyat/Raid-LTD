from odoo import api, fields, models, _
from odoo.exceptions import UserError

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
# Position of each status in the cycle (used to find the "lowest" status)
APPROVAL_SEQUENCE = {code: idx for idx, (code, _label) in enumerate(APPROVAL_STATES)}
FINAL_STATES = ('done', 'refused')

MODULE = 'hr_approval_workflow'
G_SUBMIT = f'{MODULE}.group_approval_submitter'
G_OPS = f'{MODULE}.group_approval_ops'
G_HR = f'{MODULE}.group_approval_hr'
G_FIN = f'{MODULE}.group_approval_finance'
G_CEO = f'{MODULE}.group_approval_ceo'

# key -> (allowed from states, target state, required group)
TRANSITIONS = {
    'submit': (('draft',), 'submitted', G_SUBMIT),
    'ops_approve': (('submitted',), 'ops_approved', G_OPS),
    'hr_approve': (('ops_approved',), 'hr_approved', G_HR),
    'send_finance': (('hr_approved',), 'finance', G_HR),
    'send_ceo': (('finance',), 'ceo', G_FIN),
}
# who may close, depending on the current status
CLOSE_GROUPS = {'hr_approved': G_HR, 'finance': G_FIN, 'ceo': G_CEO}
# who acts on a given status (also used for refuse and for the "My Turn" filter)
STATE_ACTOR = {
    'draft': G_SUBMIT,
    'submitted': G_OPS,
    'ops_approved': G_HR,
    'hr_approved': G_HR,
    'finance': G_FIN,
    'ceo': G_CEO,
}

# bulk buttons (list view): key -> {current status: (required group, single-record method)}
# every button only touches the selected records that are on one of its statuses
BULK = {
    'submit': {'draft': (G_SUBMIT, 'action_approval_submit')},
    'approve': {
        'submitted': (G_OPS, 'action_approval_ops_approve'),
        'ops_approved': (G_HR, 'action_approval_hr_approve'),
    },
    'send_finance': {'hr_approved': (G_HR, 'action_approval_send_finance')},
    'send_ceo': {'finance': (G_FIN, 'action_approval_send_ceo')},
    'close': {
        'hr_approved': (G_HR, 'action_approval_close'),
        'finance': (G_FIN, 'action_approval_close'),
        'ceo': (G_CEO, 'action_approval_close'),
    },
    'refuse': {
        'submitted': (G_OPS, 'action_approval_refuse'),
        'ops_approved': (G_HR, 'action_approval_refuse'),
        'hr_approved': (G_HR, 'action_approval_refuse'),
        'finance': (G_FIN, 'action_approval_refuse'),
        'ceo': (G_CEO, 'action_approval_refuse'),
    },
    'reset': {'refused': (G_SUBMIT, 'action_approval_reset')},
}


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
    # computes / search
    # ------------------------------------------------------------------
    @api.depends('approval_state')
    def _compute_approval_seq(self):
        for rec in self:
            rec.approval_seq = APPROVAL_SEQUENCE.get(rec.approval_state, 0)

    @api.model
    def _approval_user_states(self):
        """Statuses on which the current user is the one who has to act."""
        user = self.env.user
        if user.has_group('base.group_system'):
            return list(STATE_ACTOR)
        return [state for state, group in STATE_ACTOR.items() if user.has_group(group)]

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
        return [('approval_state', 'in' if positive else 'not in',
                 self._approval_user_states())]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _approval_check_group(self, group):
        user = self.env.user
        if not (user.has_group(group) or user.has_group('base.group_system')):
            raise UserError(_("You don't have the permission to perform this action."))

    def _approval_label(self, state):
        return dict(self._fields['approval_state']._description_selection(self.env))[state]

    def _approval_set(self, state):
        # permission is checked explicitly before; sudo lets approvers who do
        # not have write access on payslips / leaves move the status
        self.sudo().with_context(approval_internal=True).write({'approval_state': state})

    def write(self, vals):
        if 'approval_state' in vals and not self.env.context.get('approval_internal'):
            raise UserError(_("The approval status can only be changed through the approval buttons."))
        return super().write(vals)

    def _approval_initial_state(self):
        return 'draft'

    # ------------------------------------------------------------------
    # transitions
    # ------------------------------------------------------------------
    def _approval_transition(self, key):
        from_states, to_state, group = TRANSITIONS[key]
        self._approval_check_group(group)
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
            group = CLOSE_GROUPS.get(rec.approval_state)
            if not group:
                raise UserError(_(
                    "%(name)s (status '%(state)s') is not ready to be closed.",
                    name=rec.display_name,
                    state=rec._approval_label(rec.approval_state)))
            rec._approval_check_group(group)
        self._approval_on_done()
        self._approval_set('done')

    def action_approval_refuse(self):
        for rec in self:
            group = STATE_ACTOR.get(rec.approval_state)
            if not group or rec.approval_state == 'draft':
                raise UserError(_(
                    "%(name)s (status '%(state)s') cannot be refused.",
                    name=rec.display_name,
                    state=rec._approval_label(rec.approval_state)))
            rec._approval_check_group(group)
        self._approval_on_refused()
        self._approval_set('refused')

    def action_approval_reset(self):
        self._approval_check_group(G_SUBMIT)
        for rec in self:
            if rec.approval_state != 'refused':
                raise UserError(_("Only refused records can be reset."))
        self._approval_on_reset()
        for rec in self:
            rec._approval_set(rec._approval_initial_state())

    # ------------------------------------------------------------------
    # hooks (overridden by the concrete models)
    # ------------------------------------------------------------------
    def _approval_on_done(self):
        pass

    def _approval_on_refused(self):
        pass

    def _approval_on_reset(self):
        pass

    # ------------------------------------------------------------------
    # bulk actions (list buttons): work on mixed selections
    # ------------------------------------------------------------------
    def _approval_bulk(self, key):
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        rules = BULK[key]
        done = skipped_status = skipped_role = 0
        failed = []
        for rec in self:
            rule = rules.get(rec.approval_state)
            if not rule:
                skipped_status += 1
                continue
            group, method = rule
            if not (is_admin or user.has_group(group)):
                skipped_role += 1
                continue
            try:
                with self.env.cr.savepoint():
                    getattr(rec, method)()
                done += 1
            except UserError as e:
                failed.append("%s: %s" % (rec.display_name, e.args[0] if e.args else e))
        lines = [_("%(n)s record(s) processed.", n=done)]
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

    def action_bulk_submit(self):
        return self._approval_bulk('submit')

    def action_bulk_approve(self):
        return self._approval_bulk('approve')

    def action_bulk_send_finance(self):
        return self._approval_bulk('send_finance')

    def action_bulk_send_ceo(self):
        return self._approval_bulk('send_ceo')

    def action_bulk_close(self):
        return self._approval_bulk('close')

    def action_bulk_refuse(self):
        return self._approval_bulk('refuse')

    def action_bulk_reset(self):
        return self._approval_bulk('reset')
