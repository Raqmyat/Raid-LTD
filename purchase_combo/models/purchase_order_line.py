from uuid import uuid4

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    combo_item_id = fields.Many2one(
        'product.combo.item', string='Combo Item', copy=False,
        index=True, ondelete='cascade',
    )
    linked_line_id = fields.Many2one(
        'purchase.order.line', string='Combo Parent Line',
        ondelete='cascade', domain="[('order_id', '=', order_id)]",
        copy=False, index=True,
    )
    linked_line_ids = fields.One2many(
        'purchase.order.line', 'linked_line_id', string='Combo Component Lines',
        copy=False,
    )
    virtual_id = fields.Char(default=lambda self: str(uuid4()), copy=False, index=True)
    linked_virtual_id = fields.Char(copy=False, index=True)
    is_combo_component = fields.Boolean(compute='_compute_is_combo_component')
    combo_product_id = fields.Many2one(
        'product.product', string='Combo Product', copy=False, index=True,
    )
    combo_qty = fields.Float(string='Combo Quantity', copy=False, default=1.0)

    @api.depends('combo_item_id')
    def _compute_is_combo_component(self):
        for line in self:
            line.is_combo_component = bool(line.combo_item_id)

    @api.model
    def _get_product_id_domain(self):
        return ['|', ('purchase_ok', '=', True), ('type', '=', 'combo')]

    product_id = fields.Many2one(
        'product.product', domain=lambda self: self._get_product_id_domain(),
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Create purchase lines without expanding combos a second time.

        Combo expansion is handled by purchase.order._onchange_combo_order_line
        in the UI so components appear immediately. On save, Odoo creates the
        section and its already-generated component lines; expanding here would
        create duplicates. We still convert a combo product into a valid section
        for API/import flows, but we intentionally do not create child lines here.
        """
        prepared = []

        for vals in vals_list:
            vals = dict(vals)
            product = self.env['product.product'].browse(vals.get('product_id')).exists()
            if product and product.type == 'combo' and not vals.get('display_type'):
                combo_qty = vals.get('product_qty') or 1.0
                vals.update({
                    'display_type': 'line_section',
                    'combo_product_id': product.id,
                    'combo_qty': combo_qty,
                    'name': product.display_name,
                    'product_id': False,
                    'product_qty': 0.0,
                    'product_uom_id': False,
                    'price_unit': 0.0,
                    'date_planned': False,
                    'tax_ids': False,
                    'discount': 0.0,
                })
            prepared.append(vals)

        return super().create(prepared)

    def write(self, vals):
        result = super().write(vals)
        if 'combo_qty' in vals:
            for line in self.filtered(lambda l: l.display_type == 'line_section' and l.combo_product_id):
                line.linked_line_ids.write({'product_qty': vals['combo_qty'] or 1.0})
        return result
