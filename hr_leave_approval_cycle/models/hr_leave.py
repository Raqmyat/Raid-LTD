from odoo import api, fields, models, _
from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG
from odoo.exceptions import UserError

MODULE = 'hr_leave_approval_cycle'
GROUPS = {
    'manager': f'{MODULE}.group_leave_appr_manager',
    'hr': f'{MODULE}.group_leave_appr_hr',
    'cfo': f'{MODULE}.group_leave_appr_cfo',
    'ceo': f'{MODULE}.group_leave_appr_ceo',
}
PENDING = ('manager', 'hr', 'cfo', 'ceo')
LEAVE_APPR_STATES = [
    ('manager', 'Direct Manager'),
    ('hr', 'HR'),
    ('cfo', 'CFO'),
    ('ceo', 'CEO'),
    ('done', 'Approved'),
    ('refused', 'Refused'),
    ('cancelled', 'Cancelled'),
]
ACTIVITY = f'{MODULE}.mail_act_leave_appr'


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    leave_appr_state = fields.Selection(
        LEAVE_APPR_STATES, string='Approval Cycle', default='manager',
        required=True, tracking=True, index=True, copy=False)
    leave_appr_my_turn = fields.Boolean(
        string='My Turn (Approval Cycle)', compute='_compute_leave_appr_my_turn',
        search='_search_leave_appr_my_turn')

    # ------------------------------------------------------------------
    # My turn
    # ------------------------------------------------------------------
    @api.depends_context('uid')
    @api.depends('leave_appr_state', 'employee_id')
    def _compute_leave_appr_my_turn(self):
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        for leave in self:
            step = leave.leave_appr_state
            if step not in PENDING:
                leave.leave_appr_my_turn = False
            elif is_admin:
                leave.leave_appr_my_turn = True
            elif step == 'manager':
                leave.leave_appr_my_turn = (
                    user.has_group(GROUPS['manager'])
                    and user in leave._leave_appr_managers())
            else:
                leave.leave_appr_my_turn = user.has_group(GROUPS[step])

    def _search_leave_appr_my_turn(self, operator, value):
        if operator not in ('=', '!='):
            raise UserError(_("Unsupported operator."))
        positive = (operator == '=') == bool(value)
        user = self.env.user
        if user.has_group('base.group_system'):
            domain = [('leave_appr_state', 'in', PENDING)]
        else:
            parts = []
            if user.has_group(GROUPS['manager']):
                parts.append(['&', ('leave_appr_state', '=', 'manager'), '|',
                              ('employee_id.parent_id.user_id', '=', user.id),
                              ('employee_id.leave_manager_id', '=', user.id)])
            states = [s for s in ('hr', 'cfo', 'ceo') if user.has_group(GROUPS[s])]
            if states:
                parts.append([('leave_appr_state', 'in', states)])
            if not parts:
                domain = [('id', '=', False)]
            else:
                domain = parts[0]
                for extra in parts[1:]:
                    domain = ['|'] + domain + extra
        if positive:
            return domain
        return [('id', 'not in', self.sudo().search(domain).ids)]

    def _leave_appr_managers(self):
        self.ensure_one()
        employee = self.sudo().employee_id
        return employee.parent_id.user_id | employee.leave_manager_id

    # ------------------------------------------------------------------
    # Creation: initial status + first notification
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        for leave in leaves.filtered(lambda l: 'leave_appr_state' not in vals_list[0]):
            if leave.state == 'validate':
                # leave types without validation are approved at creation
                leave.sudo().leave_appr_state = 'done'
            elif not leave._leave_appr_managers():
                # no direct manager to ask: the request starts at HR
                leave.sudo().leave_appr_state = 'hr'
        leaves._leave_appr_schedule_activity()
        return leaves

    # ------------------------------------------------------------------
    # Notifications (one activity for the people who must act)
    # ------------------------------------------------------------------
    def _leave_appr_schedule_activity(self):
        for leave in self.sudo():
            leave.activity_unlink([ACTIVITY])
            step = leave.leave_appr_state
            if step not in PENDING:
                continue
            if step == 'manager':
                users = leave._leave_appr_managers()
            else:
                users = self.env.ref(GROUPS[step]).all_user_ids
            for user in users.filtered(lambda u: u.active and u != leave.employee_id.user_id):
                leave.activity_schedule(
                    ACTIVITY, user_id=user.id,
                    summary=_("Time off approval: %s", dict(LEAVE_APPR_STATES)[step]),
                    note=_("%(emp)s: %(type)s, %(frm)s to %(to)s",
                           emp=leave.employee_id.name,
                           type=leave.holiday_status_id.name,
                           frm=leave.request_date_from, to=leave.request_date_to))

    # ------------------------------------------------------------------
    # Permission / transition helpers
    # ------------------------------------------------------------------
    def _leave_appr_check(self, step):
        """The current user must be allowed to act on `step` for all records."""
        user = self.env.user
        if user.has_group('base.group_system'):
            return
        if not user.has_group(GROUPS[step]):
            raise UserError(_("You don't have the permission to perform this action."))
        for leave in self:
            if leave.sudo().employee_id.user_id == user:
                raise UserError(_("You cannot approve your own time off request."))
            if step == 'manager' and user not in leave._leave_appr_managers():
                raise UserError(_(
                    "Only the direct manager of %s can approve at this step.",
                    leave.employee_id.name))

    def _leave_appr_move(self, from_state, to_state):
        for leave in self:
            if leave.leave_appr_state != from_state:
                raise UserError(_(
                    "%(name)s is not waiting for this step (current: %(cur)s).",
                    name=leave.display_name,
                    cur=dict(LEAVE_APPR_STATES)[leave.leave_appr_state]))
        self._leave_appr_check(from_state)
        if to_state == 'done':
            self._leave_appr_validate()
        self.sudo().write({'leave_appr_state': to_state})
        self._leave_appr_schedule_activity()

    def _leave_appr_validate(self):
        """Closing the cycle validates the time off the standard way."""
        for leave in self:
            if leave.state in ('refuse', 'cancel'):
                raise UserError(_(
                    "%s is already refused/cancelled and cannot be approved.", leave.display_name))
        to_validate = self.filtered(lambda l: l.state in ('confirm', 'validate1'))
        if to_validate:
            # leave_fast_create skips the per-user second-approval rights check;
            # permissions are already enforced by the cycle groups.
            leaves = to_validate.sudo().with_context(leave_fast_create=True)
            leaves._action_validate(check_state=False)
            leaves.activity_update()

    # ------------------------------------------------------------------
    # Cycle buttons
    # ------------------------------------------------------------------
    def action_leave_appr_manager_approve(self):
        self._leave_appr_move('manager', 'hr')

    def action_leave_appr_hr_close(self):
        self._leave_appr_move('hr', 'done')

    def action_leave_appr_hr_to_cfo(self):
        self._leave_appr_move('hr', 'cfo')

    def action_leave_appr_cfo_close(self):
        self._leave_appr_move('cfo', 'done')

    def action_leave_appr_cfo_to_ceo(self):
        self._leave_appr_move('cfo', 'ceo')

    def action_leave_appr_ceo_close(self):
        self._leave_appr_move('ceo', 'done')

    def action_leave_appr_refuse(self):
        for leave in self:
            if leave.leave_appr_state not in PENDING:
                raise UserError(_("%s is not pending approval.", leave.display_name))
        for step in PENDING:
            step_leaves = self.filtered(lambda l: l.leave_appr_state == step)
            if step_leaves:
                step_leaves._leave_appr_check(step)
        to_refuse = self.filtered(lambda l: l.state in ('confirm', 'validate1', 'validate'))
        if to_refuse:
            to_refuse.sudo().with_context(leave_fast_create=True).action_refuse()
        self.sudo().write({'leave_appr_state': 'refused'})
        self._leave_appr_schedule_activity()

    # ------------------------------------------------------------------
    # Standard flow kept consistent with the cycle
    # ------------------------------------------------------------------
    def action_approve(self, check_state=True):
        blocked = self.filtered(
            lambda l: l.leave_appr_state != 'done' and l.validation_type != 'no_validation')
        if blocked:
            raise UserError(_(
                "Time off requests are approved through the approval cycle "
                "(Direct Manager > HR > CFO > CEO)."))
        return super().action_approve(check_state=check_state)

    def action_refuse(self):
        res = super().action_refuse()
        self.sudo().filtered(lambda l: l.leave_appr_state != 'refused').write(
            {'leave_appr_state': 'refused'})
        self._leave_appr_schedule_activity()
        return res

    def _force_cancel(self, reason=None, msg_subtype='mail.mt_comment', notify_responsibles=True):
        """Every cancellation (cycle wizard, standard Cancel, employee departure...)
        ends up here: keep the cycle status in sync."""
        res = super()._force_cancel(
            reason=reason, msg_subtype=msg_subtype, notify_responsibles=notify_responsibles)
        if not self.env.context.get(MODULE_UNINSTALL_FLAG):
            self.sudo().filtered(lambda l: l.leave_appr_state != 'cancelled').write(
                {'leave_appr_state': 'cancelled'})
            self._leave_appr_schedule_activity()
        return res

    # ------------------------------------------------------------------
    # Cancellation at ANY stage of the cycle
    # ------------------------------------------------------------------
    def _leave_appr_check_cancel(self):
        """Who may cancel: the employee himself, the direct manager of the
        employee, HR / CFO / CEO approvers, and administrators."""
        user = self.env.user
        if user.has_group('base.group_system'):
            return
        for leave in self:
            if leave.sudo().employee_id.user_id == user:
                continue
            if any(user.has_group(GROUPS[step]) for step in ('hr', 'cfo', 'ceo')):
                continue
            if user.has_group(GROUPS['manager']) and user in leave._leave_appr_managers():
                continue
            raise UserError(_(
                "You are not allowed to cancel the time off of %s.", leave.employee_id.name))

    def _leave_appr_cancel(self, reason):
        for leave in self:
            if leave.leave_appr_state in ('cancelled', 'refused') or leave.state in ('cancel', 'refuse'):
                raise UserError(_(
                    "%s is already cancelled or refused.", leave.display_name))
        self._leave_appr_check_cancel()
        for leave in self:
            leave.sudo()._force_cancel(reason, 'mail.mt_note')

    def action_leave_appr_cancel(self):
        """Opens the cancellation wizard (reason is recorded in the chatter)."""
        return {
            'type': 'ir.actions.act_window',
            'name': _("Cancel Time Off"),
            'res_model': 'leave.appr.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_model': 'hr.leave', 'active_ids': self.ids},
        }

    def action_back_to_approval(self):
        res = super().action_back_to_approval()
        for leave in self.sudo():
            leave.leave_appr_state = 'manager' if leave._leave_appr_managers() else 'hr'
        self._leave_appr_schedule_activity()
        return res
