# Time Off Approval Cycle (Odoo 19) - standalone

Request created -> Direct manager -> HR -> [Approve & Close | Send to CFO] -> CFO -> [Approve & Close | Send to CEO] -> CEO -> Approve & Close.
Refuse at any step; Reset Approval (HR) re-opens a refused request.

Independent of the payroll approval module. Own groups (Settings > Users > Human Resources):
Manager Approver (shows the buttons / menu to line managers), HR Approver, CFO Approver, CEO Approver.
The first step is decided by relationship: the employee's Time Off approver (or his manager).
No manager above the employee -> the request goes straight to HR. Nobody approves his own request
(`hr_leave_approval.allow_self_approval` = True to allow). Administrators can act on every step.

UI: Time Off form (one header row, status bar), Time Off list (select -> wizard), Time Off > Approval Cycle
(Waiting for my approval / Approve / Approve & Close / Send to CFO / Send to CEO / Refuse: wizard with everything
waiting for you, no selection). Notifications to whoever must act next and to the employee on approve/refuse.
Standard Approve/Validate/Refuse hidden and blocked (`hr_leave_approval.enforce` = False disables the block;
`hr_leave_approval.hide_buttons` = extra technical button names to hide).
IMPORTANT: uninstall `hr_leave_approval_workflow` (the previous leave module) before installing this one.
