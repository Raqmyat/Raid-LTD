from odoo import api, models

from .approval_mixin import BUTTONS
from .hr_payslip import _roles_groups
from .view_patch import approval_buttons, patch_header


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            specs = approval_buttons(
                'action_run_', lambda key: _roles_groups(self.env, 'hr.payslip', key), False)
            patch_header(arch, specs)
        return arch, view


def _make_run_method(key):
    def method(self):
        self.ensure_one()
        return self.slip_ids._approval_open_wizard(key)
    return method


# action_run_<key>: from the pay run, no selection needed - the wizard lists the
# payslips of this run that are waiting for the current user
for _key, _label, _css in BUTTONS:
    setattr(HrPayslipRun, 'action_run_%s' % _key, _make_run_method(_key))
