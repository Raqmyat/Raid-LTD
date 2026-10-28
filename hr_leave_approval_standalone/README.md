# Independent Time Off Approval Workflow (Odoo 19)

This module is standalone and depends only on `hr_holidays`; it does not import, inherit from, or depend on `hr_approval_workflow`.

## Workflow
1. Employee submits a time off request.
2. Direct manager (`employee.parent_id.user_id`) approves.
3. HR can approve and then either close the request or send it to CFO. HR can also close directly from the manager-approved stage.
4. CFO can close the request or send it to CEO.
5. CEO closes the request.

There is no Operations stage. CFO and CEO access is granted using the module's groups:
- Time Off Approval - CFO
- Time Off Approval - CEO

HR actions use the standard Odoo Time Off HR Officer group. The workflow calls Odoo's normal `action_confirm`, `action_validate`, and `action_refuse` methods so standard leave validation logic is retained.

## Upgrade / installation notes
- Back up the database before installing/upgrading.
- This is a new technical module named `hr_leave_approval_standalone`. Install and test it alongside the old module first. After verifying the new workflow, uninstall `hr_leave_approval_workflow` so its old Time Off menus/buttons are removed.
- Existing records are not forcibly remapped on upgrade. Review their `Approval Status` after upgrade.
- Assign CFO/CEO groups to the intended users.
- Test in staging first, especially with the organization's exact Odoo 19 edition and leave validation settings.
- This module does not fix the separate `hr.payslip` view error in `hr_approval_workflow` caused by missing `action_approval_reset` XPath target.
