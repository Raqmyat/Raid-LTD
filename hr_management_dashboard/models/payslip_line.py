from odoo import fields, models


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    # stored related fields => groupable / pivotable (Company > Department > Employee)
    rpt_company_id = fields.Many2one(related='slip_id.company_id', string='Company', store=True, index=True)
    rpt_department_id = fields.Many2one(related='slip_id.employee_id.department_id', string='Department', store=True, index=True)
    rpt_employee_id = fields.Many2one(related='slip_id.employee_id', string='Employee', store=True, index=True)
    rpt_date_from = fields.Date(related='slip_id.date_from', string='Period From', store=True, index=True)
    rpt_date_to = fields.Date(related='slip_id.date_to', string='Period To', store=True)
    rpt_state = fields.Selection(related='slip_id.state', string='Payslip Status', store=True)

    def action_open_payslip(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'hr.payslip',
            'res_id': self.slip_id.id, 'view_mode': 'form', 'views': [(False, 'form')],
        }
