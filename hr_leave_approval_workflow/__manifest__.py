{
    'name': 'Time Off Approval Workflow',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Time Off',
    'author': 'Custom',
    'summary': 'Same multi-level approval cycle as the payslips, applied to Time Off requests',
    'description': """
Time Off requests go through the same cycle as the payslips (module hr_approval_workflow):
Submitted -> Operations Approved -> HR Approved -> (Close | Finance -> (Close | CEO -> Close))

* A request is "Submitted" as soon as the employee creates it (leave types with "No validation" skip the cycle).
* Same buttons / roles / wizard / notifications as the payslips. Roles -> groups: Settings > Time Off Approval Roles.
* Approval buttons on the Time Off form (one row) and list (selection -> wizard), plus an
  "Approval Cycle" menu under Time Off that opens the wizard without any selection.
* The standard Approve / Validate / Refuse buttons are removed and the standard approval is blocked until
  the cycle is finished (system parameter hr_leave_approval_workflow.enforce = False disables the block).
* Closing in the cycle runs the standard validation (calendar event, work entries, balance...) in the background.
""",
    'depends': ['hr_approval_workflow', 'hr_holidays'],
    'data': [
        'data/approval_step_data.xml',
        'views/leave_menus.xml',
    ],
    'post_init_hook': '_post_init',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
