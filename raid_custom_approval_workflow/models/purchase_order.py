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

    state = fields.Selection(selection=[
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('submitted', 'Submitted'),
        ('op_manager', 'Ops Manager Approval'),
        ('finance', 'Finance Approval'),
        ('audit', 'Audit Approval'),
        ('ceo', 'CEO Approval'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

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

    def action_submit_to_manager(self):
        if not self._get_approval_setting():
            return super(PurchaseOrder, self).button_confirm()
        self.state = 'submitted'
        self._create_approval_activity('raid_custom_approval_workflow.group_purchase_ops_manager', _('Purchase Order pending Ops Manager Approval: %s', self.name))

    def action_op_manager_approve(self):
        self.state = 'op_manager'
        self._create_approval_activity('raid_custom_approval_workflow.group_purchase_finance', _('Purchase Order pending Finance Approval: %s', self.name))

    def action_finance_approve(self):
        self.state = 'finance'
        self._create_approval_activity('raid_custom_approval_workflow.group_purchase_audit', _('Purchase Order pending Audit Approval: %s', self.name))

    def action_audit_approve(self):
        self.state = 'audit'
        self._create_approval_activity('raid_custom_approval_workflow.group_purchase_ceo', _('Purchase Order pending CEO Approval: %s', self.name))

    def action_ceo_approve(self):
        self.state = 'ceo'
        # Clear activities
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def action_reject(self):
        self.state = 'draft'
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def button_confirm(self):
        if self._get_approval_setting() and self.state != 'ceo':
            raise UserError(_("You cannot confirm this order until it is approved by the CEO."))
        # Temporarily reset to 'draft' so Odoo's standard confirm check passes
        if self._get_approval_setting():
            self.sudo().write({'state': 'draft'})
        return super(PurchaseOrder, self).button_confirm()
