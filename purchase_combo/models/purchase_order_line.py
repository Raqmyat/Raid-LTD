from uuid import uuid4

from odoo import api, fields, models
from odoo.fields import Command


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    combo_product_id = fields.Many2one(
        'product.product', string='Combo Product', copy=False, index=True,
    )
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
        combo_product = self.combo_product_id or self.product_id
        if not combo_product or combo_product.type != 'combo':
            return self.env['product.combo.item']
        return combo_product.product_tmpl_id.combo_ids.combo_item_ids.filtered(
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
        """Turn a selected combo into a section and put its products underneath."""
        for line in self.filtered(lambda l: l.product_id and l.product_id.type == 'combo'):
            if not line.order_id:
                # The actual onchange will return the section state; no child rows can
                # be created until the purchase order line has an order.
                line.combo_product_id = line.product_id
                line.name = line.product_id.display_name
                line.display_type = 'line_section'
                line.product_id = False
                continue

            combo_product = line.product_id
            line.combo_product_id = combo_product
            line.name = combo_product.display_name
            line.display_type = 'line_section'
            line.product_id = False
            line.product_qty = line.product_qty or 1.0
            line.price_unit = 0.0

            children = line._get_combo_children()
            combo_items = line._get_combo_items()

            commands = [Command.delete(child._origin.id) for child in children if child._origin]
            unsaved_children = children.filtered(lambda l: not l._origin)
            if unsaved_children:
                line.order_id.order_line -= unsaved_children

            if not combo_items:
                continue

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
            if line.product_id and line.product_id.type == 'combo':
                # Keep the selected combo in a helper field, then turn this row into
                # the section header. The actual combo products are the rows below it.
                line.combo_product_id = line.product_id
                line.name = line.product_id.display_name
                line.display_type = 'line_section'
                combo_product = line.product_id
                line.product_id = False
                line._expand_combo_lines_from_product(combo_product)
                continue

            # If a combo section is changed/cleared, remove its generated children.
            if line.combo_product_id and line.display_type == 'line_section':
                children = line._get_combo_children()
                saved = [Command.delete(child._origin.id) for child in children if child._origin]
                unsaved = children.filtered(lambda l: not l._origin)
                if unsaved and line.order_id:
                    line.order_id.order_line -= unsaved
                if saved and line.order_id:
                    line.order_id.order_line = saved
                line.combo_product_id = False

    def _expand_combo_lines_from_product(self, combo_product):
        """Create component rows for a section line whose selected combo was captured."""
        for line in self:
            if not line.order_id:
                return
            children = line._get_combo_children()
            combo_items = combo_product.product_tmpl_id.combo_ids.combo_item_ids.filtered(
                lambda item: item.product_id.active
            )
            if not combo_items:
                return

            line.product_qty = line.product_qty or 1.0
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
            line.order_id.order_line = creates + updates

    @api.onchange('product_qty')
    def _onchange_combo_quantity(self):
        for line in self.filtered(lambda l: l.combo_product_id and l.display_type == 'line_section'):
            line._get_combo_children().product_qty = line.product_qty

    @api.onchange('sequence')
    def _onchange_combo_sequence(self):
        for line in self.filtered(lambda l: l.combo_product_id and l.display_type == 'line_section'):
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
                ('combo_product_id', '!=', False),
            ], limit=1)
            if parent:
                child.linked_line_id = parent.id

        # Also handle combos created through import/API where onchange is not executed.
        for line in lines.filtered(lambda l: l.product_id.type == 'combo'):
            combo_product = line.product_id
            line.combo_product_id = combo_product
            line.name = combo_product.display_name
            line.display_type = 'line_section'
            line.product_id = False
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
            self.filtered(
                lambda l: l.combo_product_id and l.display_type == 'line_section'
            )._get_combo_children().write({'product_qty': vals['product_qty']})
        return result
