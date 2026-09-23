{
    'name': 'HR Actual Salary Inputs (Bulk Editable)',
    'version': '19.0.6.0.0',
    'summary': 'Bulk-enter monthly salary inputs per employee; auto-synced into the payslip\'s real Other Inputs lines',
    'description': """
Adds a standalone, bulk-editable list (Employee / Input Type / Month / Amount)
that is completely independent from any payslip record, so entries survive
even before a payslip exists and are not reset by re-creating payslips.

When "Compute Sheet" is pressed on a payslip, any matching rows (same
employee + same month) are automatically pushed into that payslip's real
Other Inputs lines (hr.payslip.input), for whatever Input Type was chosen.
Salary rules then read them the normal Odoo way (inputs.CODE.amount), with
no custom lookup code needed.
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
