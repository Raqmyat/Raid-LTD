from . import models


def _post_init(env):
    """Existing requests must not (re)enter the cycle blindly: map them from their state."""
    Leave = env['hr.leave'].with_context(
        active_test=False, approval_internal=True, tracking_disable=True)
    mapping = [
        ('done', [('state', '=', 'validate')]),
        ('refused', [('state', 'in', ('refuse', 'cancel'))]),
        ('draft', [('state', '=', 'draft')]),
    ]
    for approval_state, domain in mapping:
        Leave.search(domain).write({'approval_state': approval_state})
    # everything else (To Approve / Second Approval) keeps the default: submitted
