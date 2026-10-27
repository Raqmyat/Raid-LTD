# HR Approval Workflow (Odoo 19)

Draft -> Submitted -> Operations Approved -> HR Approved -> Done (HR closes)
                                                         -> Finance -> Done (Finance closes)
                                                                    -> CEO -> Done (CEO closes)

Install: copy `hr_approval_workflow` to your addons path, Update Apps List, install.
Requires: hr_payroll (Enterprise), hr_holidays. Install hr_payroll_account to get the journal entry on close.
Assign roles on the user form: Payroll Submitter / Operations / HR / Finance / CEO approver.
Menu: HR Approvals > Payslip Approvals / Time Off Approvals (default filter = "My Turn").
Bulk: select records in any list > Actions > "Approve Selected".
