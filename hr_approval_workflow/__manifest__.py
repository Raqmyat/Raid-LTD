{
    'name': 'Payslip Approval Workflow',
    'version': '19.0.2.0.0',
    'category': 'Human Resources/Payroll',
    'author': 'Custom',
    'summary': 'Multi-level approval cycle on Payslips (buttons + status bar on the payslip form)',
    'description': """
Approval cycle integrated directly in the standard Payslip screens (no separate app):
Draft -> Submitted -> Operations Approved -> HR Approved -> (Close | Finance -> (Close | CEO -> Close))

* Status bar + action buttons on the payslip form.
* "Approval: My Turn" default filter + status filters / grouping on the payslip list.
* Bulk approval wizard (Actions > Approve Selected): only the lowest-status records move.
* Standard "Confirm / Create Draft Entry" is blocked until the approval cycle is finished
  (disable with system parameter hr_approval_workflow.enforce_close = False).
* Reusable `approval.mixin` so Time Off approvals can be built later in a separate module.
""",
    'depends': ['hr_payroll'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/approval_wizard_views.xml',
        'views/hr_payslip_views.xml',
        'views/default_filter.xml',
    ],
    'post_init_hook': '_post_init',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
