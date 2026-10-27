from odoo import fields, models, _
from odoo.exceptions import UserError


class HrLeave(models.Model):
    _name = 'hr.leave'
    _inherit = ['hr.leave', 'approval.mixin']

    # An employee creating a time off request *is* the submission
    approval_state = fields.Selection(default='submitted')

    def _approval_initial_state(self):
        return 'submitted'

    def _approval_on_done(self):
        to_validate = self.filtered(lambda l: l.state in ('confirm', 'validate1'))
        if to_validate:
            # leave_fast_create skips the per-user "second approval" rights check:
            # the permission was already enforced by the approval workflow groups.
            leaves = to_validate.sudo().with_context(leave_fast_create=True)
            leaves._action_validate(check_state=False)
            leaves.activity_update()

    def _approval_on_refused(self):
        to_refuse = self.filtered(lambda l: l.state in ('confirm', 'validate1', 'validate'))
        if to_refuse:
            to_refuse.sudo().with_context(leave_fast_create=True).action_refuse()

    def _approval_on_reset(self):
        if any(l.state == 'refuse' for l in self):
            raise UserError(_(
                "A refused time off request cannot be reopened. Please create a new request."))
