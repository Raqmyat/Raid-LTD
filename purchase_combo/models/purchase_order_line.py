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
        if self._origin:
            return self.order_id.order_line.filtered(
                lambda l: l.linked_line_id._origin == self._origin
            )
        return self.order_id.order_line.filtered(
            lambda l: l.linked_virtual_id == self.virtual_id
        )

    def _get_combo_items(self):
        self.ensure_one()
        return self.product_id.product_tmpl_id.combo_ids.combo_item_ids.filtered(
            lambda item: item.product_id.active
        )

    def _combo_child_vals(self, item, parent_sequence, index):
        self.ensure_one()
        product = item.product_id
        return {
            'product_id': product.id,
            'product_qty': self.product_qty or 1.0,
            'product_uom_id': product.uom_id.id,
            'price_unit': product.standard_price,
            'name': product.display_name,
            'combo_item_id': item.id,
            'linked_line_id': self.id if self._origin else False,
            'linked_virtual_id': self.virtual_id if not self._origin else False,
            'sequence': parent_sequence + index,
        }

    def _expand_combo_lines(self):
        """Create the component PO lines directly after the combo line."""
        for line in self.filtered(lambda l: l.product_id.type == 'combo'):
            if not line.order_id:
                continue

            children = line._get_combo_children()
            combo_items = line._get_combo_items()

            # Remove children from a previous combo selection.
            commands = [Command.delete(child._origin.id) for child in children if child._origin]
            unsaved_children = children.filtered(lambda l: not l._origin)
            if unsaved_children:
                line.order_id.order_line -= unsaved_children

            if not combo_items:
                continue

            line.product_qty = line.product_qty or 1.0
            # The combo parent itself carries no purchase price; the actual products do.
            line.price_unit = 0.0

            # Make room for the component lines instead of giving them the same sequence
            # as unrelated lines that already exist below the combo.
            component_count = len(combo_items)
            updates = [
                Command.update(other.id, {'sequence': other.sequence + component_count})
                for other in line.order_id.order_line
                if other.id != line.id and other.sequence > line.sequence
            ]

            creates = [
                Command.create(line._combo_child_vals(item, line.sequence, index))
                for index, item in enumerate(combo_items, start=1)
            ]
            line.order_id.order_line = commands + creates + updates

    @api.onchange('product_id')
    def _onchange_product_id_combo_expand(self):
        for line in self:
            if not line.order_id:
                continue

            if line.product_id.type != 'combo':
                children = line._get_combo_children()
                saved = [Command.delete(child._origin.id) for child in children if child._origin]
                unsaved = children.filtered(lambda l: not l._origin)
                if unsaved:
                    line.order_id.order_line -= unsaved
                if saved:
                    line.order_id.order_line = saved
                continue

            line._expand_combo_lines()

    @api.onchange('product_qty')
    def _onchange_combo_quantity(self):
        for line in self.filtered(lambda l: l.product_id.type == 'combo'):
            line._get_combo_children().product_qty = line.product_qty

    @api.onchange('sequence')
    def _onchange_combo_sequence(self):
        for line in self.filtered(lambda l: l.product_id.type == 'combo'):
            for index, child in enumerate(line._get_combo_children().sorted('sequence'), start=1):
                child.sequence = line.sequence + index

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)

        # Resolve temporary parent links after DB IDs exist.
        for child in lines.filtered(lambda l: l.combo_item_id and l.linked_virtual_id and not l.linked_line_id):
            parent = self.search([
                ('order_id', '=', child.order_id.id),
                ('virtual_id', '=', child.linked_virtual_id),
                ('product_id.type', '=', 'combo'),
            ], limit=1)
            if parent:
                child.linked_line_id = parent.id

        # Also handle combos created through import/API where onchange is not executed.
        for line in lines.filtered(lambda l: l.product_id.type == 'combo'):
            line._create_combo_components_if_missing()
        return lines

    def _create_combo_components_if_missing(self):
        for line in self:
            if line.combo_item_id or not line.order_id:
                continue
            items = line._get_combo_items()
            existing = line.linked_line_ids.mapped('combo_item_id')
            for index, item in enumerate(items.filtered(lambda x: x not in existing), start=1):
                self.env['purchase.order.line'].create(
                    line._combo_child_vals(item, line.sequence, index) | {
                        'order_id': line.order_id.id,
                        'linked_line_id': line.id,
                        'linked_virtual_id': False,
                    }
                )

    def write(self, vals):
        result = super().write(vals)
        if 'product_qty' in vals:
            self.filtered(lambda l: l.product_id.type == 'combo')._get_combo_children().write(
                {'product_qty': vals['product_qty']}
            )
        return result
