{
    'name': 'Standalone Time Off Approval Workflow',
    'version': '19.0.2.0.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Standalone manager, HR, CFO and CEO approval flow for time off',
    'description': """
Standalone Time Off approval workflow. Does not depend on hr_approval_workflow.
Flow: Employee -> Direct Manager -> HR -> (Close | CFO -> (Close | CEO -> Close)).
Operations approval is not part of this workflow.
""",
    'depends': ['hr_holidays'],
    'data': [
        'security/approval_groups.xml',
        'views/leave_menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
