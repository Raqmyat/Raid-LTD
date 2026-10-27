import ast

from odoo import api, models, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _inherit = ['hr.payslip', 'approval.mixin']

    def _approval_on_done(self):
        """Final closing: validate the payslip, which generates the accounting
        entry when the payroll accounting integration is installed."""
        to_close = self.filtered(lambda p: p.state in ('draft', 'verify'))
        if not to_close:
            return
        method = getattr(to_close.sudo(), 'action_payslip_done', None)
        if method is None:
            raise UserError(_("Cannot find the payslip validation method on this Odoo version."))
        method()

    @api.model
    def _approval_apply_default_filter(self):
        """Make "Approval: My Turn" the default filter of the standard Payslips
        menu action. The action's existing context is kept, only one key is
        merged in; if the action is missing or its context is not a plain
        dict literal, nothing is touched."""
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
