import ast

from lxml import etree

from odoo import api, models, _
from odoo.exceptions import UserError

from .approval_mixin import G_SUBMIT, G_OPS, G_HR, G_FIN, G_CEO

SYS = 'base.group_system'

# Standard buttons of the old validation cycle that are removed from the
# payslip list/form headers. Extra technical names can be added with the
# system parameter hr_approval_workflow.hide_buttons (comma separated;
# needs a server restart / module upgrade to refresh the view cache).
HIDE_NAMES = {'action_payslip_done', 'action_payslip_verify', 'action_payslip_confirm'}
HIDE_LABELS = {'validate', 'confirm', 'create draft entry'}

# (method, label, css class, groups)
LIST_BUTTONS = [
    ('action_bulk_submit', 'Submit', 'btn-primary', [G_SUBMIT, SYS]),
    ('action_bulk_approve', 'Approve', 'btn-primary', [G_OPS, G_HR, SYS]),
    ('action_bulk_send_finance', 'Send to Finance', 'btn-primary', [G_HR, SYS]),
    ('action_bulk_send_ceo', 'Send to CEO', 'btn-primary', [G_FIN, SYS]),
    ('action_bulk_close', 'Close & Post', 'btn-success', [G_HR, G_FIN, G_CEO, SYS]),
    ('action_bulk_refuse', 'Refuse', 'btn-danger', [G_OPS, G_HR, G_FIN, G_CEO, SYS]),
    ('action_bulk_reset', 'Reset Approval', 'btn-secondary', [G_SUBMIT, SYS]),
]


def patch_payslip_arch(arch, view_type, hide_names, hide_labels, buttons):
    """Remove the old validation buttons from the headers and (list view)
    put the approval buttons first. Works on any header structure."""
    for btn in arch.xpath('//header//button'):
        name = btn.get('name')
        label = (btn.get('string') or '').strip().lower()
        if name in hide_names or label in hide_labels:
            btn.getparent().remove(btn)
    if view_type == 'list' and arch.tag == 'list':
        headers = arch.xpath('./header')
        if headers:
            header = headers[0]
        else:
            header = etree.Element('header')
            arch.insert(0, header)
        for idx, (method, label, css, groups) in enumerate(buttons):
            node = etree.Element('button', {
                'name': method, 'type': 'object', 'string': label,
                'class': css, 'groups': ','.join(groups),
            })
            header.insert(idx, node)
    return arch


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'approval.mixin']

    # ------------------------------------------------------------------
    # views: old validation cycle buttons out, approval buttons in
    # ------------------------------------------------------------------
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ('list', 'form'):
            extra = self.env['ir.config_parameter'].sudo().get_param(
                'hr_approval_workflow.hide_buttons', '')
            names = HIDE_NAMES | {n.strip() for n in extra.split(',') if n.strip()}
            buttons = [(m, _(l), c, g) for m, l, c, g in LIST_BUTTONS]
            patch_payslip_arch(arch, view_type, names, HIDE_LABELS, buttons)
        return arch, view

    # ------------------------------------------------------------------
    # closing = the old "validate", now driven by the approval cycle
    # ------------------------------------------------------------------
    def _approval_on_done(self):
        """Final closing: validate the payslip (creates the accounting entry
        when hr_payroll_account is installed)."""
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
