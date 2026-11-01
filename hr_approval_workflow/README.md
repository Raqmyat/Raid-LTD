# Payslip Approval Workflow (Odoo 19)

Draft -> Submitted -> Operations Approved -> HR Approved -> Done (HR closes)
                                                         -> Finance -> Done (Finance closes)
                                                                    -> CEO -> Done (CEO closes)

No separate app. Same buttons everywhere (Submit | Approve | Send to Finance | Send to CEO |
Close & Post | Refuse | Reset Approval), same roles, same permissions:
- Payslip form: one header row (approval buttons + Compute Sheet / Cancel / Print + status bar).
  Only the buttons valid for the current status are shown.
- Payslip list: select payslips, press a button -> wizard.
- Pay Run form: press a button (no selection) -> wizard with the payslips of that run waiting for you.
- Wizard: all eligible payslips are ticked; untick the ones that should stay as they are, Confirm.
  Each record moves according to its own status; skipped / failed ones are reported.
- Settings > Payslip Approval Roles: choose the group behind each role + notify on/off.
  (Refresh the browser after changing it.)
- Notifications: when records reach a status, the members of the next role's group get an
  inbox/email notification (one message per Pay Run, not one per payslip).
- Compute Sheet only in approval status Draft. Cancel -> Refused. Set to Draft -> Draft.
- Old Validate / Confirm / Create Draft Entry buttons hidden; standard validation blocked until
  approval is Done (`hr_approval_workflow.enforce_close` = False to disable).
  Extra buttons to hide: `hr_approval_workflow.hide_buttons` (comma separated technical names).
- Existing payslips at first install: validated -> Done, cancelled -> Refused.
- Time Off approvals: separate module later, depending on this one (`approval.mixin`, `approval.step`).
- Pay button (payslip form): appears after Close & Post (approval Done + payslip validated), for the
  HR / Finance / CEO groups and anyone with Accounting access (Billing / Accountant / Adviser). It replaces the standard Pay button and calls the standard "mark as paid".
- Form buttons are per status and per role: e.g. Operations sees Approve only while the payslip is
  Submitted. Each press carries the status the user saw; if the record was already moved (double click,
  two approvers at once) it is skipped instead of being pushed one more step (rows are locked).
- Approve is split into "Approve Ops" (Submitted) and "Approve HR" (Operations Approved) on the payslip form, the
  payslip list and the Pay Run form (button + Actions menu); each one is shown only to its own role.
