from uuid import uuid4

from odoo import api, fields, models
from odoo.fields import Command


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

    def _get_combo_parent(self):
        self.ensure_one()
        if self.linked_line_id:
            return self.linked_line_id
        if self.linked_virtual_id and self.order_id:
            return self.order_id.order_line.filtered(
                lambda l: l.virtual_id == self.linked_virtual_id
            )[:1]
        return self.env['purchase.order.line']

    def _get_combo_children(self):
        self.ensure_one()
        if not self.order_id:
            return self.env['purchase.order.line']
        return self.order_id.order_line.filtered(
            lambda l: l.linked_line_id == self
            or (l.linked_virtual_id and l.linked_virtual_id == self.virtual_id)
        )

    def _get_combo_items(self):
        self.ensure_one()
        combo_product = self.combo_product_id or self.product_id
        if not combo_product:
            return self.env['product.combo.item']
        return combo_product.product_tmpl_id.combo_ids.combo_item_ids.filtered(
            lambda item: item.product_id.active
        )

    def _combo_child_vals(self, item, parent_sequence, index):
        self.ensure_one()
        product = item.product_id
        return {
            'product_id': product.id,
            'product_qty': self.combo_qty or 1.0,
            'product_uom_id': product.uom_id.id,
            'price_unit': product.standard_price,
            'name': product.display_name,
            'combo_item_id': item.id,
            'linked_line_id': self.id if self.id else False,
            'linked_virtual_id': self.virtual_id if not self.id else False,
            'sequence': parent_sequence + index,
        }

    @staticmethod
    def _section_cleanup_vals(combo_product, qty, name=None):
        """Values allowed on a non-accountable purchase order section line.

        Odoo 19 enforces a SQL constraint that section/note lines must have
        product_id, product_uom_id, date_planned, price_unit and product_uom_qty
        empty/zero. Do not leave values inherited from the product onchange.
        """
        return {
            'display_type': 'line_section',
            'product_id': False,
            'product_qty': 0.0,
            'product_uom_id': False,
            'product_uom_qty': 0.0,
            'date_planned': False,
            'price_unit': 0.0,
            'discount': 0.0,
            'tax_ids': [Command.clear()],
            'combo_product_id': combo_product.id,
            'combo_qty': qty or 1.0,
            'name': name or combo_product.display_name,
        }

    def _expand_combo_lines(self):
        """Convert the selected combo line into a section and add its products below."""
        for line in self.filtered(lambda l: l.product_id and l.product_id.type == 'combo'):
            combo_product = line.product_id
            qty = line.product_qty or 1.0

            # Keep the selected combo only in our technical combo_product_id field.
            # The actual purchase order line becomes a pure section line.
            line.combo_product_id = combo_product
            line.combo_qty = qty
            line.update(self._section_cleanup_vals(combo_product, qty))

            if not line.order_id:
                continue

            # Remove children from a previous expansion.
            children = line._get_combo_children()
            commands = [Command.delete(child.id) for child in children if child.id]
            if children.filtered(lambda l: not l.id):
                line.order_id.order_line -= children.filtered(lambda l: not l.id)

            combo_items = line._get_combo_items()
            if not combo_items:
                if commands:
                    line.order_id.order_line = commands
                continue

            component_count = len(combo_items)
            updates = [
                Command.update(other.id, {'sequence': other.sequence + component_count})
                for other in line.order_id.order_line
                if other.id != line.id
                and other.sequence > line.sequence
                and other not in children
            ]

            creates = [
                Command.create(line._combo_child_vals(item, line.sequence, index))
                for index, item in enumerate(combo_items, start=1)
            ]
            line.order_id.order_line = commands + updates + creates

    @api.onchange('product_id')
    def _onchange_product_id_combo_expand(self):
        for line in self:
            if line.product_id and line.product_id.type == 'combo':
                line._expand_combo_lines()

    @api.onchange('combo_qty')
    def _onchange_combo_quantity(self):
        for line in self.filtered(lambda l: l.display_type == 'line_section' and l.combo_product_id):
            line._get_combo_children().product_qty = line.combo_qty or 1.0

    @api.onchange('sequence')
    def _onchange_combo_sequence(self):
        for line in self.filtered(lambda l: l.display_type == 'line_section' and l.combo_product_id):
            for index, child in enumerate(line._get_combo_children().sorted('sequence'), start=1):
                child.sequence = line.sequence + index

    @api.model_create_multi
    def create(self, vals_list):
        """Create combo sections safely, then create their component products.

        We must transform combo values BEFORE calling purchase.order.line.create.
        Odoo 19 explicitly rejects product/uom/date values on a line_section.
        """
        prepared = []
        combo_data = []
        Product = self.env['product.product']

        for original_vals in vals_list:
            vals = dict(original_vals)
            combo_product = Product.browse(vals['product_id']).exists() if vals.get('product_id') else Product
            if combo_product and combo_product.type == 'combo' and vals.get('display_type') != 'line_section':
                qty = vals.get('product_qty') or 1.0
                combo_data.append((len(prepared), combo_product, qty))
                vals.update(self._section_cleanup_vals(combo_product, qty))
            prepared.append(vals)

        lines = super().create(prepared)

        for index, combo_product, qty in combo_data:
            line = lines[index]
            line._create_combo_components_if_missing()

        return lines

    def _create_combo_components_if_missing(self):
        for line in self.filtered(lambda l: l.display_type == 'line_section' and l.combo_product_id):
            if not line.order_id:
                continue
            items = line._get_combo_items()
            existing = line._get_combo_children().mapped('combo_item_id')
            for index, item in enumerate(items.filtered(lambda x: x not in existing), start=1):
                self.env['purchase.order.line'].create(
                    line._combo_child_vals(item, line.sequence, index) | {
                        'order_id': line.order_id.id,
                        'linked_line_id': line.id,
                        'linked_virtual_id': False,
                    }
                )

    def write(self, vals):
        # Odoo 19 does not allow changing display_type through write().
        # Combo sections are created with the proper display_type from the start.
        result = super().write(vals)
        if 'combo_qty' in vals:
            self.filtered(
                lambda l: l.display_type == 'line_section' and l.combo_product_id
            )._get_combo_children().write({'product_qty': vals['combo_qty'] or 1.0})
        return result
