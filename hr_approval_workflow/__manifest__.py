{
    'name': 'Payslip Approval Workflow',
    'version': '19.0.4.0.0',
    'category': 'Human Resources/Payroll',
    'author': 'Custom',
    'summary': 'Multi-level approval cycle on Payslips (buttons + status bar on the payslip form)',
    'description': """
Approval cycle integrated directly in the standard Payslip screens (no separate app):
Draft -> Submitted -> Operations Approved -> HR Approved -> (Close | Finance -> (Close | CEO -> Close))

* Same approval buttons everywhere: payslip form (one row, with Compute Sheet / Cancel / Print),
  payslip list (selection) and Pay Run form (no selection needed). The list / Pay Run buttons open a
  wizard that shows who is waiting for you and lets you untick who should stay as is.
* Roles -> groups configurable from Settings > Payslip Approval Roles (+ notify on/off per role).
* Notification (inbox / email) to the members of the group that has to act next.
* "Approval: My Turn" default filter + status filters / grouping on the payslip list.
* The old Validate / Confirm buttons are removed and the standard validation is blocked until the
  approval cycle is finished (system parameter hr_approval_workflow.enforce_close = False disables it).
* Reusable `approval.mixin` so Time Off approvals can be built later in a separate module.
""",
    'depends': ['hr_payroll'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/approval_step_data.xml',
        'views/approval_step_views.xml',
        'wizard/approval_wizard_views.xml',
        'views/hr_payslip_views.xml',
        'views/default_filter.xml',
    ],
    'post_init_hook': '_post_init',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
