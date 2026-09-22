from odoo import fields, models


class HrPayslipActualInput(models.Model):
    """Standalone master table for actual per-employee salary input values
    (e.g. Actual Basic for the month), entered directly in a bulk-editable
    list. Salary rules read this table directly at computation time, so it
    is completely independent from each payslip's own 'Other Inputs' tab
    and is NOT reset when 'Compute Sheet' is pressed.
    """
    _name = 'hr.payslip.actual.input'
    _description = 'Employee Actual Salary Input (Bulk Editable)'
    _rec_name = 'employee_id'
    _order = 'date_from desc, employee_id'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, ondelete='cascade')
    department_id = fields.Many2one(
        'hr.department', string='Department',
        related='employee_id.department_id', store=True, readonly=True)
    input_type_id = fields.Many2one(
        'hr.payslip.input.type', string='Input Type', required=True)
    date_from = fields.Date(
        string='Month', required=True,
        default=lambda self: fields.Date.today().replace(day=1),
        help='Use the first day of the target payroll month, e.g. 2026-09-01.')
    amount = fields.Float(string='Amount', required=True)
    note = fields.Char(string='Note')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company)

    _sql_constraints = [
        (
            'unique_employee_input_month',
            'unique(employee_id, input_type_id, date_from)',
            'Only one entry is allowed per employee, input type and month.',
        ),
    ]
