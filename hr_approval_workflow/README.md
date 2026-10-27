# Payslip Approval Workflow (Odoo 19)

Draft -> Submitted -> Operations Approved -> HR Approved -> Done (HR closes)
                                                         -> Finance -> Done (Finance closes)
                                                                    -> CEO -> Done (CEO closes)

No separate app. Everything is inside Payroll > Payslips (and Pay Run payslips).
- List buttons (select any mix of payslips; each button only moves the selected
  records that are on its status, the rest are skipped and reported):
  Submit | Approve (Submitted->Ops, Ops Approved->HR) | Send to Finance | Send to CEO |
  Close & Post | Refuse | Reset Approval  (+ standard Compute Sheet / Print)
- Form: approval bar (buttons + status bar). Compute Sheet only in approval status Draft.
- Cancel -> approval Refused. Set to Draft -> approval Draft. Reset Approval also re-drafts a cancelled slip.
- Old Validate / Confirm / Create Draft Entry buttons are hidden; the standard validation is blocked
  until approval is Done (system parameter `hr_approval_workflow.enforce_close` = False disables the block).
  Closing in the cycle runs the standard validation (journal entry) in the background.
- Extra standard buttons to hide: system parameter `hr_approval_workflow.hide_buttons`
  (comma separated technical names; restart/upgrade to refresh the view cache).
- Filters + group by "Approval Status" on the payslip search view; "Approval: My Turn" is the default.
- Roles: User form > Human Resources > Payroll Submitter / Operations / HR / Finance / CEO.
- Existing payslips at install: validated -> Done, cancelled -> Refused.
- Time Off approvals: separate module later, depending on this one (`approval.mixin`).
