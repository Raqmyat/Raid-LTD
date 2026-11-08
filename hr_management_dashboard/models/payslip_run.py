from odoo import api, fields, models


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    rpt_slip_count = fields.Integer(string='Payslips', compute='_compute_rpt_slip_count')
    approval_waiting_for = fields.Char(string='Waiting For', compute='_compute_approval_waiting_for')

    @api.model
    def _approval_waiting_map(self):
        """state -> who must act next, for the Raid payroll approval cycle.

        The Raid cycle stores the LAST reached stage in `state`
        (e.g. state 'legal' means "Legal/HR done, Finance is next"), so this
        translates it to the pending approver. Empty when the cycle is not installed.
        """
        if 'use_payroll_approval_cycle' not in self._fields:
            return {}
        _ = self.env._
        return {
            'draft': _('Not submitted'),
            'submitted': _('Ops Manager'),
            'op_manager': _('HR (or Legal)'),
            'hr': _('Legal'),
            'legal': _('Finance'),
            'finance': _('Audit (or CEO)'),
            'audit': _('CEO'),
            'ceo': _('Fully approved - ready to confirm'),
        }

    @api.depends('slip_ids')
    def _compute_rpt_slip_count(self):
        for run in self:
            run.rpt_slip_count = len(run.slip_ids)

    @api.depends('state')
    def _compute_approval_waiting_for(self):
        mapping = self._approval_waiting_map()
        for run in self:
            run.approval_waiting_for = mapping.get(run.state, False)
