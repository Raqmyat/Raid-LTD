{
    'name': 'HR Approval Workflow (Payroll & Time Off)',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'author': 'Custom',
    'summary': 'Multi-level approval cycle for Payslips and Time Off with bulk approval',
    'description': """
Single approval cycle shared by Payslips and Time Off:
Draft -> Submitted -> Operations Approved -> HR Approved -> (Close | Finance -> (Close | CEO -> Close))

* Bulk approval wizard: select many records, only the lowest-status ones
  are moved so everybody ends up on the same status.
* "My Turn" default filter + status filters/grouping.
""",
    'depends': ['hr_payroll', 'hr_holidays'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/approval_wizard_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_leave_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
