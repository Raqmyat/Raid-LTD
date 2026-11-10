import ast

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .approval_mixin import BULK
from .view_patch import approval_buttons, patch_header

# The approval statuses live on the STANDARD payslip `state` field, between
# Draft and Validated:
#   draft -> submitted -> ops_approved -> hr_approved -> (finance -> (ceo)) -> validated -> paid
# Close & Post is the real validation of the payslip (validated) + posting of its entry.
APPROVAL_STATES = [
    ('submitted', 'Submitted'),
    ('ops_approved', 'Operations Approved'),
    ('hr_approved', 'HR Approved'),
    ('finance', 'Finance'),
    ('ceo', 'CEO'),
]
NEW_STATES = tuple(code for code, _label in APPROVAL_STATES)
# statuses in which the payslip is NOT validated yet
PRE_VALIDATION_STATES = ('draft',) + NEW_STATES
STATUSBAR_VISIBLE = 'draft,submitted,ops_approved,hr_approved,finance,ceo,validated,paid'

# Buttons of the old validation cycle that are removed from the payslip
# headers. Extra technical names: system parameter hr_approval_workflow.hide_buttons
# (comma separated; restart / upgrade to refresh the view cache).
# The standard Pay button (action_register_payment) is NOT touched.
HIDE_NAMES = {'action_payslip_done', 'action_validate'}
HIDE_LABELS = {'validate', 'confirm', 'create draft entry'}


def _roles_groups(env, model, key, state=None):
    """Group xmlids allowed to see the button `key` (from the configuration).
    With `state`, only the role that acts on that status."""
    Step = env['approval.step']
    xmlids = []
    for st, (role, _method) in BULK[key].items():
        if state and st != state:
            continue
        xmlid = Step._group_xmlid_for(model, role)
        if xmlid and xmlid not in xmlids:
            xmlids.append(xmlid)
    return xmlids + ['base.group_system']


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'approval.mixin']
    _approval_field = 'state'

    state = fields.Selection(
        selection_add=APPROVAL_STATES + [('validated',)],
        ondelete={code: 'set default' for code in NEW_STATES})
    approval_my_turn = fields.Boolean(
        string='My Turn', compute='_compute_approval_my_turn',
        search='_search_approval_my_turn')

    # ------------------------------------------------------------------
    # permissions on the status
    # ------------------------------------------------------------------
    def _approval_guarded_values(self):
        # the standard statuses (draft / validated / paid / cancel) keep being written by
        # payroll itself; only the approval ones are reserved to the approval buttons
        return NEW_STATES

    def write(self, vals):
        self._approval_check_write(vals)
        return super().write(vals)

    @api.depends_context('uid')
    @api.depends('state')
    def _compute_approval_my_turn(self):
        states = self._approval_user_states()
        for rec in self:
            rec.approval_my_turn = rec.state in states

    @api.depends('state', 'error_count', 'warning_count')
    def _compute_state_display(self):
        # state_display only knows the standard statuses: an approval status shows as Draft there
        # (the real approval status has its own column / the status bar)
        pending = self.filtered(lambda p: p.state in NEW_STATES)
        for slip in pending:
            slip.state_display = (
                'error' if slip.error_count else 'warning' if slip.warning_count else 'draft')
        super(HrPayslip, self - pending)._compute_state_display()

    # ------------------------------------------------------------------
    # views: old validation buttons out, approval buttons in
    # ------------------------------------------------------------------
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ('list', 'form'):
            extra = self.env['ir.config_parameter'].sudo().get_param(
                'hr_approval_workflow.hide_buttons', '')
            names = HIDE_NAMES | {n.strip() for n in extra.split(',') if n.strip()}

            def groups_for(key, state=None):
                return _roles_groups(self.env, 'hr.payslip', key, state)

            if view_type == 'form':
                # direct buttons + the approval statuses in the standard status bar,
                # same row as Compute Sheet / Cancel / Print. The standard Pay button
                # is left alone: it shows once the payslip is really validated.
                specs = approval_buttons('action_btn_', groups_for, True)
                patch_header(arch, specs, names, HIDE_LABELS, statusbar_visible=STATUSBAR_VISIBLE)
            else:
                # selection -> wizard
                specs = approval_buttons('action_wizard_', groups_for, False)
                patch_header(arch, specs, names, HIDE_LABELS)
        return arch, view

    # ------------------------------------------------------------------
    # wizard / notification details
    # ------------------------------------------------------------------
    def _approval_wizard_line_vals(self):
        vals = super()._approval_wizard_line_vals()
        currency = self.company_id.currency_id
        net = getattr(self, 'net_wage', 0.0) or 0.0
        period = ''
        if self.date_from and self.date_to:
            period = '%s → %s' % (self.date_from, self.date_to)
        run = self.payslip_run_id.name or ''
        vals.update({
            'name': self.employee_id.name or self.display_name,
            'extra': '%s%s  |  %s %s' % (
                (run + '  |  ') if run else '', period,
                format(net, ',.%df' % (currency.decimal_places or 2)), currency.name or ''),
        })
        return vals

    def _approval_notify_name(self):
        return self.employee_id.name or self.display_name

    def _approval_notify_targets(self):
        targets = []
        for run in self.mapped('payslip_run_id'):
            slips = self.filtered(lambda p, run=run: p.payslip_run_id == run)
            if hasattr(run, 'message_notify'):
                targets.append((run, slips))
            else:
                targets.extend((s, s) for s in slips)
        targets.extend((s, s) for s in self.filtered(lambda p: not p.payslip_run_id))
        return targets

    def _approval_check_transition(self, key):
        if key == 'submit':
            empty = self.filtered(lambda p: not p.line_ids)
            if empty:
                raise UserError(_(
                    "Compute the sheet before submitting:\n%s",
                    '\n'.join(empty.mapped('display_name'))))

    # ------------------------------------------------------------------
    # Close & Post = the REAL validation (+ posting of the journal entry)
    # ------------------------------------------------------------------
    def _approval_finish(self):
        """Same as the standard Validate button (action_payslip_done: status Validated and the
        accounting entry), then the entry is posted, so that the standard Pay button
        (which needs a validated payslip with a POSTED entry) can be used.
        If anything fails the whole close is cancelled and the status does not change."""
        slips = self.sudo()
        slips.with_context(approval_closing=True, payslip_generate_pdf=True).action_payslip_done()
        stuck = slips.filtered(lambda p: p.state != 'validated')
        if stuck:
            raise UserError(_(
                "The standard validation did not complete for:\n%s\n"
                "Close & Post was cancelled.", '\n'.join(stuck.mapped('display_name'))))
        post = self.env['ir.config_parameter'].sudo().get_param(
            'hr_approval_workflow.post_entry', 'True')
        if post not in ('False', '0') and 'move_id' in self._fields:
            moves = slips.mapped('move_id').filtered(lambda m: m.state == 'draft')
            if moves:
                moves.action_post()

    def action_payslip_done(self):
        """Block the standard validation until the approval cycle is complete
        (only Close & Post validates)."""
        if not self.env.context.get('approval_closing'):
            enforce = self.env['ir.config_parameter'].sudo().get_param(
                'hr_approval_workflow.enforce_close', 'True')
            if enforce not in ('False', '0'):
                pending = self.filtered(lambda p: p.state in PRE_VALIDATION_STATES)
                if pending:
                    raise UserError(_(
                        "These payslips must go through the approval workflow (Close & Post) "
                        "before they can be validated:\n%s",
                        '\n'.join(pending.mapped('display_name'))))
        return super().action_payslip_done()

    # ------------------------------------------------------------------
    # Refuse = the standard cancel (Set to Draft brings it back)
    # ------------------------------------------------------------------
    def _approval_refuse(self):
        self.sudo().with_context(approval_internal=True).action_payslip_cancel()
        self._approval_notify()

    @api.model
    def _approval_apply_default_filter(self):
        """Make "Approval: My Turn" the default filter of the Payslips menu action."""
        action = self.env.ref('hr_payroll.action_view_hr_payslip_form', raise_if_not_found=False)
        if not action:
            return
        try:
            ctx = ast.literal_eval(action.context or '{}')
        except (ValueError, SyntaxError):
            return
        if not isinstance(ctx, dict) or 'search_default_approval_my_turn' in ctx:
            return
        ctx['search_default_approval_my_turn'] = 1
        action.context = repr(ctx)
