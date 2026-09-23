{
    'name': 'HR Payslip Actual Inputs (Tags)',
    'version': '19.0.1.0.0',
    'summary': 'Add multiple Other Inputs per employee directly from the Payslips list, as tags',
    'description': """
Exposes the payslip's real Other Inputs lines (hr.payslip.input) directly
in the Payslips list view as tags. Click the field, pick an existing Input
Type or create a new line (Input Type + Amount) on the spot, and add as
many as needed for the same employee/payslip. No separate table, no menu,
no syncing: this writes straight into the standard Odoo model that Salary
Rules already read via inputs.CODE.amount.
""",
    'category': 'Human Resources/Payroll',
    'author': 'Custom',
    'depends': ['hr_payroll'],
    'data': [
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
