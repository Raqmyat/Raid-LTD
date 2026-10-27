from odoo import models, _
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
