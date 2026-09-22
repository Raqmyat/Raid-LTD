from odoo import fields, models


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        related='payslip_id.employee_id',
        store=True,
        readonly=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='payslip_id.employee_id.department_id',
        store=True,
        readonly=True,
    )
    date_from = fields.Date(
        string='From',
        related='payslip_id.date_from',
        store=True,
        readonly=True,
    )
    date_to = fields.Date(
        string='To',
        related='payslip_id.date_to',
        store=True,
        readonly=True,
    )
    payslip_state = fields.Selection(
        related='payslip_id.state',
        string='Payslip Status',
        store=True,
        readonly=True,
    )
