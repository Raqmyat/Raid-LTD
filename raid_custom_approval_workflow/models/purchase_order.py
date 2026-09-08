# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    raid_linked_so_id = fields.Many2one('sale.order', string="Linked Sales Order")
    use_purchase_approval_cycle = fields.Boolean(compute='_compute_use_purchase_approval_cycle')

    # Tracks which branch of the approval cycle this order took after the HR
    # Manager's decision, purely so the status bar can show only the relevant
    # path instead of mixing both branches together.
    approval_path = fields.Selection(selection=[
        ('finance', 'Finance'),
        ('legal', 'Legal'),
    ], copy=False)

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
        ('submitted', 'Ops Manager'),
        ('to_hr', 'HR Manager'),
        ('to_finance', 'Finance'),
        ('to_ceo_finance', 'CEO'),
        ('finance_done', 'Ready for Payment'),
        ('ceo_done_finance', 'CEO Approved'),
        ('to_legal', 'Legal'),
        ('to_audit', 'Audit'),
        ('to_cfo', 'Finance'),
        ('to_ceo_cfo', 'CEO'),
        ('cfo_done', 'Ready for PO'),
        ('ceo_done_cfo', 'CEO Approved'),
        # --- Standard Odoo states ---
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    # States from which the order is fully approved and only needs the final
    # "Confirm" click to turn into an actual Purchase Order.
    _READY_TO_CONFIRM_STATES = ('finance_done', 'cfo_done', 'ceo_done_finance', 'ceo_done_cfo')

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
        self.approval_path = 'finance'
        self._create_approval_activity(
            'raid_custom_approval_workflow.group_purchase_finance',
            _('Purchase Order pending Finance Approval: %s', self.name)
        )

    def action_hr_send_to_legal(self):
        self.state = 'to_legal'
        self.approval_path = 'legal'
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
        self.state = 'ceo_done_finance'
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
            _('Purchase Order pending Finance Approval: %s', self.name)
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
        self.state = 'ceo_done_cfo'
        self._clear_approval_activities()

    # ------------------------------------------------------------------
    # Reject - sends the order back exactly one step, to whoever made the
    # previous decision (not to Draft), and re-notifies them with a new
    # "To-do" activity so they know it came back.
    # ------------------------------------------------------------------
    _REJECT_MAP = {
        'submitted': ('draft', None, 'Purchase Order returned to Draft for correction: %s'),
        'to_hr': ('submitted', 'raid_custom_approval_workflow.group_purchase_ops_manager',
                  'Purchase Order returned - pending Ops Manager Approval: %s'),
        'to_finance': ('to_hr', 'raid_custom_approval_workflow.group_purchase_hr',
                       'Purchase Order returned - pending HR Manager Decision: %s'),
        'to_ceo_finance': ('to_finance', 'raid_custom_approval_workflow.group_purchase_finance',
                            'Purchase Order returned - pending Finance Approval: %s'),
        'to_legal': ('to_hr', 'raid_custom_approval_workflow.group_purchase_hr',
                     'Purchase Order returned - pending HR Manager Decision: %s'),
        'to_audit': ('to_legal', 'raid_custom_approval_workflow.group_purchase_legal',
                     'Purchase Order returned - pending Legal Approval: %s'),
        'to_cfo': ('to_audit', 'raid_custom_approval_workflow.group_purchase_audit',
                   'Purchase Order returned - pending Audit Approval: %s'),
        'to_ceo_cfo': ('to_cfo', 'raid_custom_approval_workflow.group_purchase_finance',
                       'Purchase Order returned - pending Finance Approval: %s'),
    }

    def action_reject(self):
        for order in self:
            mapping = order._REJECT_MAP.get(order.state)
            if not mapping:
                # Unknown/unmapped state - fall back to the old safe behavior.
                order.state = 'draft'
                order._clear_approval_activities()
                continue

            previous_state, group_xml_id, summary = mapping
            order.state = previous_state
            if group_xml_id:
                order._create_approval_activity(group_xml_id, _(summary, order.name))
            else:
                # No group for Draft - notify whoever originally created it.
                order._clear_approval_activities()
                if order.create_uid:
                    order.activity_schedule(
                        'mail.mail_activity_data_todo',
                        summary=_(summary, order.name),
                        user_id=order.create_uid.id,
                    )

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
