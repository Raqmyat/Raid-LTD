from odoo import api, fields, models

from .payslip import APPROVAL_FLOW, waiting_map


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    rpt_slip_count = fields.Integer(string='Payslips', compute='_compute_rpt_counts')
    rpt_cnt_draft = fields.Integer(string='Draft', compute='_compute_rpt_counts')
    rpt_cnt_submitted = fields.Integer(string='Submitted', compute='_compute_rpt_counts')
    rpt_cnt_ops = fields.Integer(string='Ops Approved', compute='_compute_rpt_counts')
    rpt_cnt_hr = fields.Integer(string='HR Approved', compute='_compute_rpt_counts')
    rpt_cnt_finance = fields.Integer(string='Finance', compute='_compute_rpt_counts')
    rpt_cnt_ceo = fields.Integer(string='CEO', compute='_compute_rpt_counts')
    rpt_cnt_validated = fields.Integer(string='Validated', compute='_compute_rpt_counts')
    rpt_cnt_paid = fields.Integer(string='Paid', compute='_compute_rpt_counts')
    rpt_cnt_cancel = fields.Integer(string='Cancelled', compute='_compute_rpt_counts')
    rpt_stage = fields.Selection(
        [('empty', 'No Payslips'), ('draft', 'Not Submitted'), ('submitted', 'Submitted'),
         ('ops_approved', 'Operations Approved'), ('hr_approved', 'HR Approved'),
         ('finance', 'Finance'), ('ceo', 'CEO'), ('closed', 'Validated / Paid')],
        string='Approval Stage', compute='_compute_rpt_counts', search='_search_rpt_stage',
        help='The EARLIEST stage still holding a payslip of this pay run (the run moves only as '
             'fast as its slowest payslip).')
    approval_waiting_for = fields.Char(string='Waiting For', compute='_compute_rpt_counts')

    @api.depends('slip_ids.state')
    def _compute_rpt_counts(self):
        data = {}
        for run, state, count in self.env['hr.payslip']._read_group(
                [('payslip_run_id', 'in', self.ids)], ['payslip_run_id', 'state'], ['__count']):
            data.setdefault(run.id, {})[state] = count
        waiting = waiting_map(self.env)
        for run in self:
            c = data.get(run.id, {})
            run.rpt_slip_count = sum(c.values())
            run.rpt_cnt_draft = c.get('draft', 0)
            run.rpt_cnt_submitted = c.get('submitted', 0)
            run.rpt_cnt_ops = c.get('ops_approved', 0)
            run.rpt_cnt_hr = c.get('hr_approved', 0)
            run.rpt_cnt_finance = c.get('finance', 0)
            run.rpt_cnt_ceo = c.get('ceo', 0)
            run.rpt_cnt_validated = c.get('validated', 0)
            run.rpt_cnt_paid = c.get('paid', 0)
            run.rpt_cnt_cancel = c.get('cancel', 0)
            stage = next((s for s in APPROVAL_FLOW if c.get(s)), False)
            if stage:
                run.rpt_stage = stage
            elif c.get('validated') or c.get('paid'):
                run.rpt_stage = 'closed'
            else:
                run.rpt_stage = 'empty'
            run.approval_waiting_for = waiting.get(stage, False)

    def _search_rpt_stage(self, operator, value):
        """Searchable through the payslips (the stage is derived from them)."""
        if operator not in ('=', '!=', 'in', 'not in'):
            return [('id', '=', 0)]
        values = value if isinstance(value, (list, tuple)) else [value]
        runs = self.search([])
        wanted = runs.filtered(lambda r: r.rpt_stage in values)
        positive = operator in ('=', 'in')
        return [('id', 'in' if positive else 'not in', wanted.ids)]
