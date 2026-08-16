from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseComboConfigurator(models.TransientModel):
    _name = 'purchase.combo.configurator'
    _description = "Add a Combo Product (and all its components) to a Purchase Order"

    order_id = fields.Many2one(
        comodel_name='purchase.order',
        string="Purchase Order",
        required=True,
    )
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template',
        string="Combo Product",
        required=True,
        domain=[('type', '=', 'combo')],
        help="Select the Combo product you want to add to this Purchase Order. "
             "All of its components will be added automatically.",
    )

    def action_confirm(self):
        self.ensure_one()
        if not self.product_tmpl_id:
            raise UserError(_("Please select a Combo product first."))

        combo_items = self.product_tmpl_id.combo_ids.combo_item_ids
        if not combo_items:
            raise UserError(_("This Combo product has no components configured."))

        PurchaseOrderLine = self.env['purchase.order.line']

        parent_product = self.product_tmpl_id.product_variant_id
        parent_line = PurchaseOrderLine.create({
            'order_id': self.order_id.id,
            'product_id': parent_product.id,
            'product_qty': 1.0,
            'price_unit': 0.0,
            'name': self.product_tmpl_id.display_name,
        })

        for item in combo_items:
            PurchaseOrderLine.create({
                'order_id': self.order_id.id,
                'product_id': item.product_id.id,
                'product_qty': 1.0,
                'price_unit': item.product_id.standard_price,
                'name': item.product_id.display_name,
                'combo_item_id': item.id,
                'linked_line_id': parent_line.id,
            })

        return {'type': 'ir.actions.act_window_close'}

