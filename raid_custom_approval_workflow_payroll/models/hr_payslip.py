# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    """Same approval cycle as purchase.order, applied to a single Payslip.

    NOTE: if a payslip belongs to a Batch (payslip_run_id is set), the cycle is
    driven at the BATCH level (see HrPayslipRun below) and NOT per payslip -
    that's the "batch لكل الموظفين" case. The buttons below are only meant to
    be shown (see views/hr_payslip_views.xml) when payslip_run_id is empty.
    """
    _inherit = 'hr.payslip'

    use_payroll_approval_cycle = fields.Boolean(compute='_compute_use_payroll_approval_cycle')

    # IMPORTANT: verify these base state values against your actual hr.payslip
    # model (Community vs Enterprise payroll differ). Adjust selection_add
    # values/order if your base states are named differently.
    state = fields.Selection(selection_add=[
        ('submitted', 'Submitted'),
        ('op_manager', 'Ops Manager Approval'),
        ('hr', 'HR Approval'),
        ('legal', 'Legal Approval'),
        ('finance', 'Finance Approval'),
        ('audit', 'Audit Approval'),
        ('ceo', 'CEO Approval'),
    ], ondelete={
        'submitted': 'set default',
        'op_manager': 'set default',
        'hr': 'set default',
        'legal': 'set default',
        'finance': 'set default',
        'audit': 'set default',
        'ceo': 'set default',
    })

    def _compute_use_payroll_approval_cycle(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'raid_custom_approval_workflow.use_payroll_approval_cycle')
        for slip in self:
            slip.use_payroll_approval_cycle = bool(enabled)

    def _get_approval_setting(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'raid_custom_approval_workflow.use_payroll_approval_cycle')

    def _create_approval_activity(self, group_xml_id, summary):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            return
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        existing = self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type)
        existing.unlink()
        for user in group.all_user_ids:
            self.activity_schedule('mail.mail_activity_data_todo', summary=summary, user_id=user.id)

    # ---------------- Approval actions (mirrors purchase.order) ----------------
    def action_submit_to_manager(self):
        if not self._get_approval_setting():
            return self.action_payslip_done()
        self.write({'state': 'submitted'})
        for slip in self:
            slip._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_ops_manager',
                _('Payslip pending Ops Manager Approval: %s', slip.name))

    def action_op_manager_approve(self):
        self.write({'state': 'op_manager'})
        for slip in self:
            slip._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_hr',
                _('Payslip pending HR Approval: %s', slip.name))

    def action_hr_approve(self):
        self.write({'state': 'legal'})
        for slip in self:
            slip._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_finance',
                _('Payslip pending Finance Approval: %s', slip.name))

    def action_send_to_legal(self):
        self.write({'state': 'hr'})
        for slip in self:
            slip._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_legal',
                _('Payslip pending Legal Approval: %s', slip.name))

    def action_legal_approve(self):
        self.write({'state': 'legal'})
        for slip in self:
            slip._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_finance',
                _('Payslip pending Finance Approval: %s', slip.name))

    def action_finance_approve(self):
        self.write({'state': 'finance'})
        for slip in self:
            slip._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_audit',
                _('Payslip pending Audit Approval: %s', slip.name))

    def action_audit_approve(self):
        self.write({'state': 'ceo'})
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def action_send_to_ceo(self):
        self.write({'state': 'audit'})
        for slip in self:
            slip._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_ceo',
                _('Payslip pending CEO Approval: %s', slip.name))

    def action_ceo_approve(self):
        self.write({'state': 'ceo'})
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def action_reject(self):
        self.write({'state': 'draft'})
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def action_payslip_done(self):
        """Gate the final confirmation ('Create Draft Entry' / done step).
        Payslips that belong to a Batch are skipped here - the Batch gates them
        instead (see HrPayslipRun.action_validate)."""
        to_check = self.filtered(lambda s: not s.payslip_run_id)
        if to_check and to_check[0]._get_approval_setting():
            not_ready = to_check.filtered(lambda s: s.state != 'ceo')
            if not_ready:
                raise UserError(_(
                    "You cannot confirm this payslip until it is approved by the CEO: %s"
                ) % ', '.join(not_ready.mapped('name')))
            to_check.sudo().write({'state': 'draft'})
        return super(HrPayslip, self).action_payslip_done()


class HrPayslipRun(models.Model):
    """Same approval cycle as purchase.order, applied to a Payslip Batch
    (Payslips Run). Approving the Batch cascades approval to every payslip
    inside it - so nobody has to approve each employee's payslip one by one
    when salaries are processed for everyone via a batch."""
    _inherit = 'hr.payslip.run'

    use_payroll_approval_cycle = fields.Boolean(compute='_compute_use_payroll_approval_cycle')

    # NOTE: verify base states of hr.payslip.run in your version
    # (commonly draft / verify / close).
    state = fields.Selection(selection_add=[
        ('submitted', 'Submitted'),
        ('op_manager', 'Ops Manager Approval'),
        ('hr', 'HR Approval'),
        ('legal', 'Legal Approval'),
        ('finance', 'Finance Approval'),
        ('audit', 'Audit Approval'),
        ('ceo', 'CEO Approval'),
    ], ondelete={
        'submitted': 'set default',
        'op_manager': 'set default',
        'hr': 'set default',
        'legal': 'set default',
        'finance': 'set default',
        'audit': 'set default',
        'ceo': 'set default',
    })

    def _compute_use_payroll_approval_cycle(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param(
            'raid_custom_approval_workflow.use_payroll_approval_cycle')
        for run in self:
            run.use_payroll_approval_cycle = bool(enabled)

    def _get_approval_setting(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'raid_custom_approval_workflow.use_payroll_approval_cycle')

    def _create_approval_activity(self, group_xml_id, summary):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            return
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        if 'activity_ids' not in self._fields:
            return
        existing = self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type)
        existing.unlink()
        for user in group.all_user_ids:
            self.activity_schedule('mail.mail_activity_data_todo', summary=summary, user_id=user.id)

    def action_submit_to_manager(self):
        self.write({'state': 'submitted'})
        for run in self:
            run._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_ops_manager',
                _('Payslips Batch pending Ops Manager Approval: %s', run.name))

    def action_op_manager_approve(self):
        self.write({'state': 'op_manager'})
        for run in self:
            run._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_hr',
                _('Payslips Batch pending HR Approval: %s', run.name))

    def action_hr_approve(self):
        self.write({'state': 'legal'})
        for run in self:
            run._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_finance',
                _('Payslips Batch pending Finance Approval: %s', run.name))

    def action_send_to_legal(self):
        self.write({'state': 'hr'})
        for run in self:
            run._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_legal',
                _('Payslips Batch pending Legal Approval: %s', run.name))

    def action_legal_approve(self):
        self.write({'state': 'legal'})
        for run in self:
            run._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_finance',
                _('Payslips Batch pending Finance Approval: %s', run.name))

    def action_finance_approve(self):
        self.write({'state': 'finance'})
        for run in self:
            run._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_audit',
                _('Payslips Batch pending Audit Approval: %s', run.name))

    def action_audit_approve(self):
        self.write({'state': 'ceo'})
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        if 'activity_ids' in self._fields:
            self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def action_send_to_ceo(self):
        self.write({'state': 'audit'})
        for run in self:
            run._create_approval_activity(
                'raid_custom_approval_workflow.group_payroll_ceo',
                _('Payslips Batch pending CEO Approval: %s', run.name))

    def action_ceo_approve(self):
        self.write({'state': 'ceo'})
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        if 'activity_ids' in self._fields:
            self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def action_reject(self):
        self.write({'state': 'draft'})
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        if 'activity_ids' in self._fields:
            self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def action_validate(self):
        """This is the method that (in stock Odoo) confirms/generates entries
        for the whole batch. ADAPT THE METHOD NAME to whatever your version
        actually calls when the batch is finally confirmed/closed."""
        if self._get_approval_setting():
            not_ready = self.filtered(lambda r: r.state != 'ceo')
            if not_ready:
                raise UserError(_(
                    "You cannot confirm this Payslips Batch until it is approved by the CEO: %s"
                ) % ', '.join(not_ready.mapped('name')))
            self.sudo().write({'state': 'draft'})
            # Cascade: mark every payslip in the batch as CEO-approved so that
            # HrPayslip.action_payslip_done() lets them through without asking
            # for a per-employee approval.
            for run in self:
                run.slip_ids.write({'state': 'ceo'})
        return super(HrPayslipRun, self).action_validate()
