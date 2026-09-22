{
    'name': 'HR Payslip Input Editable List',
    'version': '19.0.1.0.0',
    'summary': 'Bulk edit Payslip Other Inputs (e.g. Actual Basic) from one editable list view',
    'description': """
Adds a menu under Payroll to view and edit all hr.payslip.input records
(salary inputs, e.g. Actual Basic) in one editable list, instead of opening
each payslip individually.
""",
    'category': 'Human Resources/Payroll',
    'author': 'Custom',
    'depends': ['hr_payroll'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payslip_input_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
