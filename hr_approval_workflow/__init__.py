from . import models
from . import wizard


def _post_init(env):
    """Records that existed before the installation must not enter the cycle."""
    Payslip = env['hr.payslip'].with_context(
        approval_internal=True, tracking_disable=True, active_test=False)
    finished = Payslip.search([('state', 'not in', ('draft', 'verify', 'cancel'))])
    finished.write({'approval_state': 'done'})
    cancelled = Payslip.search([('state', '=', 'cancel')])
    cancelled.write({'approval_state': 'refused'})
