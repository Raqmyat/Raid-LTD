import ast

from odoo import api, models, _
from odoo.exceptions import UserError

from .approval_mixin import BULK
from .view_patch import approval_buttons, patch_header

# Buttons of the old validation cycle that are removed from the payslip
# headers. Extra technical names: system parameter hr_approval_workflow.hide_buttons
# (comma separated; restart / upgrade to refresh the view cache).
HIDE_NAMES = {'action_payslip_done', 'action_payslip_verify', 'action_payslip_confirm'}
HIDE_LABELS = {'validate', 'confirm', 'create draft entry'}


def _roles_groups(env, model, key):
    """Group xmlids allowed to see the button `key` (from the configuration)."""
    Step = env['approval.step']
    xmlids = []
    for role, _method in BULK[key].values():
        xmlid = Step._group_xmlid_for(model, role)
        if xmlid and xmlid not in xmlids:
            xmlids.append(xmlid)
    return xmlids + ['base.group_system']


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'approval.mixin']

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

            def groups_for(key):
                return _roles_groups(self.env, 'hr.payslip', key)

            if view_type == 'form':
                # direct buttons + status bar, same row as Compute Sheet / Cancel / Print
                specs = approval_buttons('action_btn_', groups_for, True)
                patch_header(arch, specs, names, HIDE_LABELS, statusbar=True)
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
        vals.update({
            'name': self.employee_id.name or self.display_name,
            'extra': '%s  |  %s %s' % (period, format(net, ',.%df' % (currency.decimal_places or 2)),
                                       currency.name or ''),
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

    # ------------------------------------------------------------------
    # closing = the old "validate", now driven by the approval cycle
    # ------------------------------------------------------------------
    def _approval_on_done(self):
        to_close = self.filtered(lambda p: p.state in ('draft', 'verify'))
        if not to_close:
            return
        if not hasattr(to_close, 'action_payslip_done'):
            raise UserError(_("Cannot find the payslip validation method on this Odoo version."))
        to_close.sudo().with_context(approval_closing=True).action_payslip_done()

    def action_payslip_done(self):
        """Block the standard validation until the approval cycle is complete."""
        if not self.env.context.get('approval_closing'):
            enforce = self.env['ir.config_parameter'].sudo().get_param(
                'hr_approval_workflow.enforce_close', 'True')
            if enforce not in ('False', '0'):
                pending = self.filtered(lambda p: p.approval_state != 'done')
                if pending:
                    raise UserError(_(
                        "These payslips must go through the approval workflow before "
                        "they can be validated:\n%s",
                        '\n'.join(pending.mapped('display_name'))))
        return super().action_payslip_done()

    # ------------------------------------------------------------------
    # Compute / Cancel / Set to Draft stay available, tied to the approval status
    # ------------------------------------------------------------------
    def compute_sheet(self):
        locked = self.filtered(lambda p: p.approval_state != 'draft')
        if locked:
            raise UserError(_(
                "The sheet can only be computed while the approval status is Draft "
                "(use Reset Approval / Set to Draft first):\n%s",
                '\n'.join(locked.mapped('display_name'))))
        return super().compute_sheet()

    def action_payslip_cancel(self):
        if any(p.approval_state == 'done' for p in self):
            raise UserError(_("A payslip whose approval is Done can no longer be cancelled."))
        res = super().action_payslip_cancel()
        self.filtered(lambda p: p.approval_state != 'refused')._approval_set('refused')
        return res

    def action_payslip_draft(self):
        res = super().action_payslip_draft()
        self._approval_set('draft')
        return res

    def _approval_on_reset(self):
        cancelled = self.filtered(lambda p: p.state == 'cancel')
        if cancelled:
            cancelled.sudo().action_payslip_draft()

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
