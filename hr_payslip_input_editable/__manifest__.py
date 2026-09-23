{
    'name': 'HR Actual Salary Inputs (Bulk Editable)',
    'version': '19.0.3.0.0',
    'summary': 'Bulk-enter actual monthly salary inputs (e.g. Actual Basic) per employee, read directly by salary rules',
    'description': """
Adds a standalone, bulk-editable list (Employee / Input Type / Month / Amount)
that is completely independent from each payslip's own "Other Inputs" tab.
Salary rules can query this table directly at computation time (via
env['hr.payslip.actual.input']), so the values are never lost when
"Compute Sheet" is pressed on a payslip.
""",
    'category': 'Human Resources/Payroll',
    'author': 'Custom',
    'depends': ['hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payslip_actual_input_views.xml',
        'views/hr_payslip_tree_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
