from . import models
from . import wizard


def _post_init(env):
    """Requests that existed before the installation: map them from their standard state."""
    Leave = env['hr.leave'].with_context(
        active_test=False, lv_internal=True, tracking_disable=True)
    for leave in Leave.search([]):
        leave.write({'leave_approval_state': leave._lv_initial_state()})
