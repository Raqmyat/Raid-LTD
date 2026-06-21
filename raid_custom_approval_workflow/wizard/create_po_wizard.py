# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreatePoWizard(models.TransientModel):
    _name = 'create.po.wizard'
    _description = 'Create Purchase Order from Sale Order'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    vendor_id = fields.Many2one('res.partner', string="Vendor", domain=[('supplier_rank', '>', 0)])
    create_po = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string="Do you want to create a purchase order?", default='yes', required=True)

    def action_confirm(self):
        self.ensure_one()
        # Try context first (most reliable), then fall back to stored field
        sale_order_id = self.env.context.get('active_id') or self.sale_order_id.id
        if not sale_order_id:
            raise UserError(_("No Sales Order found. Please try again."))

        sale_order = self.env['sale.order'].browse(sale_order_id)
        if not sale_order.exists():
            raise UserError(_("Sales Order not found. Please try again."))

        if self.create_po == 'yes':
            if not self.vendor_id:
                raise UserError(_("Please select a vendor to create a purchase order."))

            po_vals = {
                'partner_id': self.vendor_id.id,
                'raid_linked_so_id': sale_order.id,
                'company_id': sale_order.company_id.id,
                'origin': sale_order.name,
                'order_line': [],
            }
            if 'raid_sale_order_id' in self.env['purchase.order']._fields:
                po_vals['raid_sale_order_id'] = sale_order.id

            for line in sale_order.order_line:
                if not line.display_type and line.product_id:
                    po_vals['order_line'].append((0, 0, {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'product_qty': line.product_uom_qty,
                        'analytic_distribution':line.analytic_distribution,
                        'price_unit': line.product_id.standard_price,
                        'date_planned': fields.Datetime.now(),
                    }))

            po = self.env['purchase.order'].create(po_vals)
            
            # Log in chatter for debugging
            sale_order.message_post(body=_("Purchase Order created: %s") % po.name)

        # Move Sale Order to 'submitted' state
        return sale_order.action_submit_to_manager()
