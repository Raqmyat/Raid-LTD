{
    'name': 'Time Off Approval Cycle',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Time Off',
    'author': 'Custom',
    'summary': 'Manager -> HR -> (Close | CFO -> (Close | CEO)) approval cycle for Time Off requests',
    'description': """
Standalone approval cycle for Time Off (independent of the payroll approval module, own groups):

  Request created -> Direct manager -> HR -> HR decides: Approve & Close  |  Send to CFO
                                       CFO decides: Approve & Close  |  Send to CEO
                                       CEO: Approve & Close

* Direct manager = the employee's Time Off approver (or the employee's manager).
* Groups: Manager Approver, HR Approver, CFO Approver, CEO Approver (Settings > Users > Time Off Approval Cycle).
* Buttons on the Time Off form (one row), on the list (selection -> wizard) and an "Approval Cycle" menu
  under Time Off that opens the wizard without selecting anything.
* Notification (inbox / email) to whoever has to act next, and to the employee when approved / refused.
* Standard Approve / Validate / Refuse are removed and blocked until the cycle is finished.
""",
    'depends': ['hr_holidays', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/approval_wizard_views.xml',
        'views/leave_menus.xml',
    ],
    'post_init_hook': '_post_init',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
