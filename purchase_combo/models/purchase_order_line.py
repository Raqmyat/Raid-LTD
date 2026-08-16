from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    combo_item_id = fields.Many2one(
        comodel_name='product.combo.item',
        string="Combo Item",
        help="If this line was generated from a Combo product, this is the specific "
             "combo choice/item it represents.",
    )
    linked_line_id = fields.Many2one(
        comodel_name='purchase.order.line',
        string="Linked Order Line",
        ondelete='cascade',
        domain="[('order_id', '=', order_id)]",
        copy=False,
        index=True,
        help="The parent Combo line this line was generated from.",
    )
    linked_line_ids = fields.One2many(
        comodel_name='purchase.order.line',
        inverse_name='linked_line_id',
        string="Linked Order Lines",
    )

    @api.model
    def _get_product_id_domain(self):
        # Standard Odoo restricts the product selector to purchase_ok=True products.
        # Combo products are usually not flagged purchase_ok (they're a Sales concept),
        # so we explicitly widen the domain to also allow them.
        return ['|', ('purchase_ok', '=', True), ('type', '=', 'combo')]

    product_id = fields.Many2one(domain=lambda self: self._get_product_id_domain())

    @api.onchange('product_id')
    def _onchange_product_id_combo_expand(self):
        """When a Combo product is picked, automatically add one line per
        combo component (no manual choice), linked back to this line."""
        if not self.product_id or self.product_id.type != 'combo':
            return

        combo_items = self.product_id.product_tmpl_id.combo_ids.combo_item_ids
        if not combo_items:
            return

        self.name = self.product_id.display_name
        self.product_qty = 1.0
        self.price_unit = 0.0

        new_lines = [(0, 0, {
            'product_id': item.product_id.id,
            'product_qty': 1.0,
            'price_unit': item.product_id.standard_price,
            'name': item.product_id.display_name,
            'combo_item_id': item.id,
            'linked_line_id': self.id,
        }) for item in combo_items]

        self.order_id.order_line = new_lines

