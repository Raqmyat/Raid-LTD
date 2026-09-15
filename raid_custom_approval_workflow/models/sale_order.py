# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state = fields.Selection(selection=[
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('submitted', 'Submitted'),
        ('op_manager', 'Ops Manager Approval'),
        ('hr', 'HR Approval'),
        ('audit', 'Audit Approval'),
        ('ceo', 'CEO Approval'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')

    # Stored field - updated directly from wizard when PO is created
    purchase_order_ids = fields.One2many('purchase.order', 'raid_linked_so_id', string='Purchase Orders')
    purchase_order_count = fields.Integer(
        string='Purchase Order Count',
        compute='_compute_purchase_order_count',
        compute_sudo=True,
    )
    use_sale_approval_cycle = fields.Boolean(compute='_compute_use_sale_approval_cycle')

    def _build_link_domain_for_field(self, po_model, field_name):
        """Build a compatible domain for different field types."""
        field = po_model._fields.get(field_name)
        if not field:
            return []
        if field.type == 'many2one' and getattr(field, 'comodel_name', False) == 'sale.order':
            return [(field_name, '=', self.id)]
        if field.type in ('char', 'text'):
            return [(field_name, 'ilike', self.name)]
        if field.type in ('integer', 'float', 'monetary'):
            return [(field_name, '=', self.id)]
        return []

    def _get_related_purchase_orders(self):
        """Return all POs linked to this SO across known link styles."""
        self.ensure_one()
        po_model = self.env['purchase.order'].sudo()
        po_fields = po_model._fields
        purchase_orders = po_model.browse()

        if 'raid_linked_so_id' in po_fields:
            link_domain = self._build_link_domain_for_field(po_model, 'raid_linked_so_id')
            if link_domain:
                purchase_orders |= po_model.search(link_domain)
        if 'raid_sale_order_id' in po_fields:
            link_domain = self._build_link_domain_for_field(po_model, 'raid_sale_order_id')
            if link_domain:
                purchase_orders |= po_model.search(link_domain)
        # Fallback for flows that only set PO origin to SO number.
        if 'origin' in po_fields and self.name:
            purchase_orders |= po_model.search([('origin', 'ilike', self.name)])

        return purchase_orders

    def _get_po_action_domain(self):
        """Domain used by smart button list view."""
        self.ensure_one()
        po_model = self.env['purchase.order']
        po_fields = po_model._fields
        domain_parts = []
        if 'raid_linked_so_id' in po_fields:
            domain_parts.extend(self._build_link_domain_for_field(po_model, 'raid_linked_so_id'))
        if 'raid_sale_order_id' in po_fields:
            domain_parts.extend(self._build_link_domain_for_field(po_model, 'raid_sale_order_id'))
        if 'origin' in po_fields and self.name:
            domain_parts.append(('origin', 'ilike', self.name))

        if not domain_parts:
            return [('id', '=', 0)]
        if len(domain_parts) == 1:
            return domain_parts
        # Build OR domain for 2+ conditions.
        or_domain = ['|'] * (len(domain_parts) - 1)
        return or_domain + domain_parts

    @api.depends('purchase_order_ids')
    def _compute_purchase_order_count(self):
        for order in self:
            order.purchase_order_count = len(order._get_related_purchase_orders())

    def _compute_use_sale_approval_cycle(self):
        enabled = self.env['ir.config_parameter'].sudo().get_param('raid_custom_approval_workflow.use_sale_approval_cycle')
        for order in self:
            order.use_sale_approval_cycle = bool(enabled)

    def _get_approval_setting(self):
        return self.env['ir.config_parameter'].sudo().get_param('raid_custom_approval_workflow.use_sale_approval_cycle')

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
        self.ensure_one()
        if not self._get_approval_setting():
            return super(SaleOrder, self).action_confirm()

        self.state = 'submitted'
        self._create_approval_activity('raid_custom_approval_workflow.group_sale_ops_manager', _('Sales Order pending Ops Manager Approval: %s', self.name))

    def action_op_manager_approve(self):
        self.state = 'op_manager'
        self._create_approval_activity('raid_custom_approval_workflow.group_sale_hr', _('Sales Order pending HR Approval: %s', self.name))

    def action_hr_approve(self):
        self.state = 'hr'
        self._create_approval_activity('raid_custom_approval_workflow.group_sale_audit', _('Sales Order pending Audit Approval: %s', self.name))

    def action_audit_approve(self):
        self.state = 'ceo'
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def action_send_to_ceo(self):
        self.state = 'audit'
        self._create_approval_activity(
            'raid_custom_approval_workflow.group_sale_ceo',
            _('Sales Order pending CEO Approval: %s', self.name),
        )

    def action_ceo_approve(self):
        self.state = 'ceo'
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def action_reject(self):
        self.state = 'draft'
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        self.activity_ids.filtered(lambda a: a.activity_type_id == activity_type).unlink()

    def action_view_raid_purchase_orders(self):
        self.ensure_one()
        pos = self._get_related_purchase_orders()
        visible_pos = self.env['purchase.order'].search([('id', 'in', pos.ids)])
        domain = self._get_po_action_domain()
        if pos and not visible_pos:
            raise UserError(_(
                "Linked Purchase Orders exist for %s, but you don't have access to view them. "
                "Please check company assignment and purchase access rights."
            ) % self.name)
        if not pos:
            raise UserError(_("No linked Purchase Orders were found for %s.") % self.name)
        if len(visible_pos) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'form',
                'res_id': visible_pos.id,
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', visible_pos.ids)],
            'context': {
                'default_raid_linked_so_id': self.id,
                'default_raid_sale_order_id': self.id,
                'default_origin': self.name,
            },
            'target': 'current',
        }

    # Keep compatibility if another caller still uses the old method name.
    def action_view_purchase_orders(self):
        return self.action_view_raid_purchase_orders()

    def action_confirm(self):
        if self._get_approval_setting() and self.state != 'ceo':
            raise UserError(_("You cannot confirm this order until it is approved by the CEO."))
        # Temporarily reset to 'draft' so Odoo's standard confirm check passes
        if self._get_approval_setting():
            self.sudo().write({'state': 'draft'})
        return super(SaleOrder, self).action_confirm()
