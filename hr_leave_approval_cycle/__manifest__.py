{
    'name': 'Time Off Approval Cycle',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Time Off',
    'author': 'Custom',
    'summary': 'Direct Manager -> HR -> (Close | CFO -> (Close | CEO)) approval cycle for Time Off',
    'description': """
Dedicated approval cycle for Time Off requests, with its own security groups.

    Request created -> Direct Manager -> HR -> Approve & Close
                                            -> Send to CFO -> Approve & Close
                                                           -> Send to CEO -> Approve & Close

The request can be cancelled at ANY stage (also after it was approved), with a
recorded reason, by the employee, his direct manager, HR, CFO or CEO.

The standard Approve / Validate / Refuse / Cancel buttons are replaced by the cycle; when the
cycle is closed the time off is validated normally (balance, calendar, payroll).
""",
    'depends': ['hr_holidays', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/rules.xml',
        'data/mail_activity_type.xml',
        'views/hr_leave_views.xml',
        'wizard/cancel_wizard_views.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
