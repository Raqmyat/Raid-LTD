{
    'name': 'HR Payslip Actual Inputs (Tags)',
    'version': '19.0.5.0.0',
    'summary': 'Add multiple Other Inputs per employee directly from the Payslips list, as tags',
    'description': """
Exposes the payslip's real Other Inputs lines (hr.payslip.input) directly
in the Payslips list view via a custom widget. Click "+" to instantly see
the Input Types available for the employee's Salary Structure, pick one,
and enter the Amount right there - no separate table, no menu, no syncing:
this writes straight into the standard Odoo model that Salary Rules
already read via inputs.CODE.amount.
""",
    'category': 'Human Resources/Payroll',
    'author': 'Custom',
    'depends': ['hr_payroll'],
    'data': [
        'views/hr_payslip_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_payslip_actual_inputs_tags/static/src/js/actual_inputs_field.js',
            'hr_payslip_actual_inputs_tags/static/src/xml/actual_inputs_field.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
