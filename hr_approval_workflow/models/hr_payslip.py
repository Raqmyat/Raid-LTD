import ast

from odoo import api, models, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'approval.mixin']

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
