# Payslip Approval Workflow (Odoo 19)

Draft -> Submitted -> Operations Approved -> HR Approved -> Done (HR closes)
                                                         -> Finance -> Done (Finance closes)
                                                                    -> CEO -> Done (CEO closes)

No separate app/menu: everything lives inside Payroll > Payslips.
- Payslip form: approval bar (buttons + status bar) above the sheet.
- Payslip list: "Approval Status" column, filters, "Approval: My Turn" (default).
- Bulk: select payslips > Actions > "Approve Selected".
- Roles (User form > Human Resources): Payroll Submitter / Operations / HR / Finance / CEO approver.
- Standard Confirm is blocked until approval is Done. To disable:
  System Parameter `hr_approval_workflow.enforce_close` = False.
- Existing payslips at install time: validated -> Done, cancelled -> Refused.
- Time Off approvals: to be built as a separate module depending on this one (uses `approval.mixin`).

Upgrade from 1.0: Apps > update this module (leave approvals/menu are removed).
