# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    raid_linked_so_id = fields.Many2one('sale.order', string="Linked Sales Order")
    use_purchase_approval_cycle = fields.Boolean(compute='_compute_use_purchase_approval_cycle')

    def _compute_use_purchase_approval_cycle(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param('raid_custom_approval_workflow.use_purchase_approval_cycle')
        for order in self:
            order.use_purchase_approval_cycle = bool(enabled)

    # NOTE ON STATE NAMES:
    # Every state below is named after what actually happened / what is actually
    # pending. This matters for the chatter log: the "state" field is tracked
    # (tracking=3), so Odoo automatically writes a log line every time it changes,
    # e.g. "Status: Pending HR Manager Decision -> Pending Finance Approval".
    # As long as we never assign a state that doesn't match the real step, the log
    # can never show a step that was actually skipped.
    state = fields.Selection(selection=[
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        # --- Custom purchase approval cycle ---
        ('submitted', 'Pending Ops Manager Approval'),
        ('to_hr', 'Pending HR Manager Decision'),
        ('to_finance', 'Pending Finance Approval'),
        ('to_ceo_finance', 'Pending CEO Approval (Finance path)'),
        ('finance_done', 'Finance Approved - Ready for Payment'),
        ('to_legal', 'Pending Legal Approval'),
        ('to_audit', 'Pending Audit Approval'),
        ('to_cfo', 'Pending CFO Approval'),
        ('to_ceo_cfo', 'Pending CEO Approval (CFO path)'),
        ('cfo_done', 'CFO Approved - Ready for Purchase Order'),
        # --- Standard Odoo states ---
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    # States from which the order is fully approved and only needs the final
    # "Confirm" click to turn into an actual Purchase Order.
    _READY_TO_CONFIRM_STATES = ('finance_done', 'cfo_done')

    # All "pending approval" states - used to show/hide the Reject button.
    _PENDING_STATES = ('submitted', 'to_hr', 'to_finance', 'to_ceo_finance', 'to_legal', 'to_audit', 'to_cfo', 'to_ceo_cfo')

    def _get_approval_setting(self):
        return self.env['ir.config_parameter'].sudo().get_param('raid_custom_approval_workflow.use_purchase_approval_cycle')

    def _create_approval_activity(self, group_xml_id, summary):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            return

        # Clear existing approval activities
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        existing = self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type)
        existing.unlink()

        for user in group.all_user_ids:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=summary,
                user_id=user.id
            )

    def _clear_approval_activities(self):
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    # ------------------------------------------------------------------
    # Step 1: Ops Assistant submits (unchanged)
    # ------------------------------------------------------------------
    def action_submit_to_manager(self):
        if not self._get_approval_setting():
            return super(PurchaseOrder, self).button_confirm()
        self.state = 'submitted'
        self._create_approval_activity(
            'raid_custom_approval_workflow.group_purchase_ops_manager',
            _('Purchase Order pending Ops Manager Approval: %s', self.name)
        )

    # ------------------------------------------------------------------
    # Step 2: Ops Manager approves -> goes to HR Manager for a decision
    # ------------------------------------------------------------------
    def action_op_manager_approve(self):
        self.state = 'to_hr'
        self._create_approval_activity(
            'raid_custom_approval_workflow.group_purchase_hr',
            _('Purchase Order pending HR Manager Decision: %s', self.name)
        )

    # ------------------------------------------------------------------
    # Step 3: HR Manager decision - exactly 2 options
    # ------------------------------------------------------------------
    def action_hr_send_to_finance(self):
        self.state = 'to_finance'
        self._create_approval_activity(
            'raid_custom_approval_workflow.group_purchase_finance',
            _('Purchase Order pending Finance Approval: %s', self.name)
        )

    def action_hr_send_to_legal(self):
        self.state = 'to_legal'
        self._create_approval_activity(
            'raid_custom_approval_workflow.group_purchase_legal',
            _('Purchase Order pending Legal Approval: %s', self.name)
        )

    # ------------------------------------------------------------------
    # Path A: Finance approves directly -> DONE, ready for payment.
    # Finance can optionally escalate to CEO first instead of closing directly.
    # ------------------------------------------------------------------
    def action_finance_approve(self):
        self.state = 'finance_done'
        self._clear_approval_activities()

    def action_finance_send_to_ceo(self):
        self.state = 'to_ceo_finance'
        self._create_approval_activity(
            'raid_custom_approval_workflow.group_purchase_ceo',
            _('Purchase Order pending CEO Approval: %s', self.name)
        )

    def action_ceo_approve_from_finance(self):
        self.state = 'finance_done'
        self._clear_approval_activities()

    # ------------------------------------------------------------------
    # Path B: Legal -> Audit -> CFO
    # CFO can optionally escalate to CEO first instead of closing directly.
    # ------------------------------------------------------------------
    def action_legal_approve(self):
        self.state = 'to_audit'
        self._create_approval_activity(
            'raid_custom_approval_workflow.group_purchase_audit',
            _('Purchase Order pending Audit Approval: %s', self.name)
        )

    def action_audit_approve(self):
        self.state = 'to_cfo'
        self._create_approval_activity(
            'raid_custom_approval_workflow.group_purchase_finance',
            _('Purchase Order pending CFO Approval: %s', self.name)
        )

    def action_cfo_approve(self):
        self.state = 'cfo_done'
        self._clear_approval_activities()

    def action_cfo_send_to_ceo(self):
        self.state = 'to_ceo_cfo'
        self._create_approval_activity(
            'raid_custom_approval_workflow.group_purchase_ceo',
            _('Purchase Order pending CEO Approval: %s', self.name)
        )

    def action_ceo_approve_from_cfo(self):
        self.state = 'cfo_done'
        self._clear_approval_activities()

    # ------------------------------------------------------------------
    # Reject - available at any pending stage, sends back to draft.
    # ------------------------------------------------------------------
    def action_reject(self):
        self.state = 'draft'
        self._clear_approval_activities()

    # ------------------------------------------------------------------
    # Final confirmation - only allowed once fully approved via either path.
    # ------------------------------------------------------------------
    def button_confirm(self):
        if self._get_approval_setting() and self.state not in self._READY_TO_CONFIRM_STATES:
            raise UserError(_("You cannot confirm this order until it has completed the approval cycle."))
        # Temporarily reset to 'draft' so Odoo's standard confirm check passes
        if self._get_approval_setting():
            self.sudo().write({'state': 'draft'})
        return super(PurchaseOrder, self).button_confirm()
