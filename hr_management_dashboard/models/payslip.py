from odoo import api, fields, models

# Approval statuses (hr_approval_workflow) -> who has to act next
APPROVAL_FLOW = ['draft', 'submitted', 'ops_approved', 'hr_approved', 'finance', 'ceo']
PENDING_STATES = tuple(APPROVAL_FLOW)           # not validated yet
APPROVAL_STATES = tuple(APPROVAL_FLOW[1:])      # inside the approval cycle (submitted -> ceo)
CLOSED_STATES = ('validated', 'paid')


def waiting_map(env):
    _ = env._
    return {
        'draft': _('Submitter (not submitted yet)'),
        'submitted': _('Operations (approve)'),
        'ops_approved': _('HR (approve / send to Finance)'),
        'hr_approved': _('HR (close or send to Finance)'),
        'finance': _('Finance (close or send to CEO)'),
        'ceo': _('CEO (close)'),
    }


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    rpt_waiting_for = fields.Char(string='Waiting For', compute='_compute_rpt_waiting_for')
    rpt_approval_group = fields.Selection([
        ('draft', 'Not Submitted'),
        ('approval', 'In Approval'),
        ('closed', 'Validated / Paid'),
        ('cancel', 'Cancelled / Refused'),
    ], string='Approval Stage', compute='_compute_rpt_approval_group', search='_search_rpt_approval_group')

    @api.depends('state')
    def _compute_rpt_waiting_for(self):
        mapping = waiting_map(self.env)
        for slip in self:
            slip.rpt_waiting_for = mapping.get(slip.state, False)

    @api.depends('state')
    def _compute_rpt_approval_group(self):
        for slip in self:
            if slip.state == 'draft':
                slip.rpt_approval_group = 'draft'
            elif slip.state in APPROVAL_STATES:
                slip.rpt_approval_group = 'approval'
            elif slip.state in CLOSED_STATES:
                slip.rpt_approval_group = 'closed'
            else:
                slip.rpt_approval_group = 'cancel'

    def _search_rpt_approval_group(self, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            return [('id', '=', 0)]
        groups = {
            'draft': ['draft'],
            'approval': list(APPROVAL_STATES),
            'closed': list(CLOSED_STATES),
        }
        values = value if isinstance(value, (list, tuple)) else [value]
        positive = operator in ('=', 'in')
        chosen = [g for g in groups if (g in values) == positive]
        states = [st for g in chosen for st in groups[g]]
        cancelled = [('state', 'not in', list(PENDING_STATES) + list(CLOSED_STATES))]
        want_cancel = ('cancel' in values) == positive
        domain = [('state', 'in', states)] if states else [('id', '=', 0)]
        if want_cancel:
            domain = ['|'] + domain + cancelled
        return domain
