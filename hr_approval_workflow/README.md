# Payslip Approval Workflow (Odoo 19)

The approval statuses are values of the STANDARD payslip `state` field (no separate status field):

    Draft -> Submitted -> Operations Approved -> HR Approved -> Validated (HR closes) -> Paid
                                                             -> Finance -> Validated (Finance closes)
                                                                        -> CEO -> Validated (CEO closes)

- Close & Post = the real validation of the payslip (standard `action_payslip_done`: status Validated +
  accounting entry) and the journal entry is posted. If the validation fails the close is cancelled with
  an error and the status does not change. Set `hr_approval_workflow.post_entry` = False to leave the entry draft.
- After Close & Post, Odoo's own Pay button (`action_register_payment`) shows by itself: it is not hidden or
  replaced. It needs: status Validated, a POSTED entry, `Batch Account Move Lines` OFF on the company, and the
  Accounting "Billing" group. (With Batch Account Move Lines ON, Odoo hides the Pay button of the payslip by
  design: the payment is made on the shared journal entry.)
- Same buttons everywhere (Submit | Approve Ops | Approve HR | Send to Finance | Send to CEO | Close & Post | Refuse):
  - Payslip form: one header row (approval buttons + Compute Sheet / Cancel / Print), only the buttons valid
    for the current status and role are shown.
  - Payslip list: select payslips, press a button -> wizard.
  - Pay Run form: press a button (no selection) -> wizard with the payslips of that run waiting for you.
  - Wizard: all eligible payslips are ticked; untick the ones that should stay as they are, Confirm.
    Close & Post on several payslips validates them together (one journal entry in batch mode).
- Refuse = the standard Cancel. Set to Draft (standard button) brings a cancelled payslip back to Draft.
- Settings > Payslip Approval Roles: choose the group behind each role + notify on/off (refresh the browser after).
- Notifications: the members of the next role's group get an inbox/email notification (one per Pay Run).
- Compute Sheet only in Draft (standard). Submit needs a computed sheet.
- Old Validate / Confirm / Create Draft Entry buttons hidden; standard validation blocked until the payslip is
  closed here (`hr_approval_workflow.enforce_close` = False to disable). Extra buttons to hide:
  `hr_approval_workflow.hide_buttons` (comma separated technical names).
- The Pay Run stays Ready while one of its payslips is in the approval cycle.
- The list shows the real status in the "Approval Status" column (the standard status column shows Draft for
  payslips that are still in the approval cycle).
- Do not install together with `raid_custom_approval_workflow_payroll` (same statuses on `state`).
