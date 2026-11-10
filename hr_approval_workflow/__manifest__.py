{
    'name': 'Payslip Approval Workflow',
    'version': '19.0.5.0.0',
    'category': 'Human Resources/Payroll',
    'author': 'Custom',
    'summary': 'Multi-level approval cycle on Payslips (buttons + status bar on the payslip form)',
    'description': """
Approval cycle built on the STANDARD status (`state`) of the payslip - no separate status field:
Draft -> Submitted -> Operations Approved -> HR Approved -> (Finance -> (CEO)) -> Validated -> Paid

* Close & Post (HR / Finance / CEO) = the REAL validation of the payslip (standard
  action_payslip_done: status Validated + accounting entry) and the entry is posted
  (system parameter hr_approval_workflow.post_entry = False to leave the entry in draft).
  If the validation fails the close is cancelled and the status does not change.
* After that the STANDARD Odoo Pay button appears by itself (nothing replaces or hides it).
* Same approval buttons everywhere: payslip form (one row, with Compute Sheet / Cancel / Print),
  payslip list (selection) and Pay Run form (no selection needed). The list / Pay Run buttons open a
  wizard that shows who is waiting for you and lets you untick who should stay as is.
* Refuse = standard Cancel; Set to Draft (standard) brings it back.
* Roles -> groups configurable from Settings > Payslip Approval Roles (+ notify on/off per role).
* Notification (inbox / email) to the members of the group that has to act next.
* "Approval: My Turn" default filter + status filters / grouping on the payslip list.
* The old Validate / Confirm buttons are removed and the standard validation is blocked until the
  payslip is closed here (system parameter hr_approval_workflow.enforce_close = False disables it).
* A pay run stays "Ready" while any of its payslips is still in the approval cycle.
* Do NOT install together with raid_custom_approval_workflow_payroll (same statuses on `state`).
""",
    'depends': ['hr_payroll', 'hr_payroll_account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/approval_step_data.xml',
        'views/approval_step_views.xml',
        'wizard/approval_wizard_views.xml',
        'views/hr_payslip_views.xml',
        'views/payslip_run_actions.xml',
        'views/default_filter.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
