# Time Off Approval Workflow (Odoo 19)

Depends on `hr_approval_workflow` (mixin, roles, wizard, notifications) and `hr_holidays`.

Submitted (when the employee creates the request) -> Operations Approved -> HR Approved ->
Done (HR closes) | Finance -> Done (Finance closes) | CEO -> Done (CEO closes).

- Leave types with "No validation" never enter the cycle (approval status = Done).
- Time Off form: approval buttons + status bar in the header row. Time Off list: select -> button -> wizard.
- Time Off > Approval Cycle > Approve / Send to Finance / Send to CEO / Close & Post / Refuse:
  opens the wizard with every request waiting for you (no selection). Untick who should stay, Confirm.
- Roles -> groups: Settings > Time Off Approval Roles (separate from the payslip roles).
- Close = standard validation in the background; Refuse = standard refusal; Reset Approval re-opens a refused request.
- Standard Approve / Validate / Refuse buttons hidden and the standard approval blocked until Done
  (`hr_leave_approval_workflow.enforce` = False disables the block; `hr_leave_approval_workflow.hide_buttons`
  = extra technical button names to hide).
- Existing requests at install: Approved -> Done, Refused/Cancelled -> Refused, To Approve -> Submitted.
