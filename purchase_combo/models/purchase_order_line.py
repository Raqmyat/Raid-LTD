from uuid import uuid4

from odoo import api, fields, models, _
from odoo.fields import Command


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    combo_item_id = fields.Many2one(
        comodel_name='product.combo.item',
        string='Combo Item',
        copy=False,
        index=True,
        ondelete='cascade',
        help='The combo item that generated this purchase order line.',
    )
    linked_line_id = fields.Many2one(
        comodel_name='purchase.order.line',
        string='Combo Parent Line',
        ondelete='cascade',
        domain="[('order_id', '=', order_id)]",
        copy=False,
        index=True,
        help='The parent combo purchase order line.',
    )
    linked_line_ids = fields.One2many(
        comodel_name='purchase.order.line',
        inverse_name='linked_line_id',
        string='Combo Component Lines',
        copy=False,
    )
    # Same idea used by Odoo Sales for unsaved parent/child lines.
    virtual_id = fields.Char(default=lambda self: str(uuid4()), copy=False, index=True)
    linked_virtual_id = fields.Char(copy=False, index=True)

    is_combo_component = fields.Boolean(
        string='Combo Component',
        compute='_compute_is_combo_component',
        store=False,
    )

    @api.depends('combo_item_id')
    def _compute_is_combo_component(self):
        for line in self:
            line.is_combo_component = bool(line.combo_item_id)

    @api.model
    def _get_product_id_domain(self):
        # Odoo normally excludes combo products from purchasing because combos
        # are primarily a Sales feature. This module intentionally allows them.
        return ['|', ('purchase_ok', '=', True), ('type', '=', 'combo')]

    product_id = fields.Many2one(
        comodel_name='product.product',
        domain=lambda self: self._get_product_id_domain(),
    )

    def _combo_component_commands(self, combo_items, quantity):
        self.ensure_one()
        commands = []
        parent_virtual_id = self.virtual_id or str(uuid4())
        for index, item in enumerate(combo_items, start=1):
            product = item.product_id
            commands.append(Command.create({
                'product_id': product.id,
                'product_qty': quantity,
                'product_uom': product.uom_po_id.id,
                'price_unit': product.standard_price,
                'name': product.display_name,
                'combo_item_id': item.id,
                'linked_line_id': self.id if self._origin else False,
                'linked_virtual_id': parent_virtual_id if not self._origin else False,
                # Put components immediately after their combo parent.
                'sequence': (self.sequence or 10) + index,
            }))
        return commands

    def _remove_combo_component_commands(self):
        """Build commands that remove the existing children of combo lines.

        For unsaved children, unlinking their NewId is handled by the x2many
        command protocol when the command is applied to the current cache.
        """
        commands = []
        for line in self.linked_line_ids:
            if line._origin:
                commands.append(Command.delete(line._origin.id))
        return commands

    @api.onchange('product_id')
    def _onchange_product_id_combo_expand(self):
        for line in self:
            if not line.order_id or not line.product_id:
                continue

            # If a normal product replaced an old combo, remove its children.
            if line.product_id.type != 'combo':
                old_children = line.order_id.order_line.filtered(
                    lambda l: (
                        (l.linked_line_id == line)
                        or (l.linked_virtual_id and l.linked_virtual_id == line.virtual_id)
                    )
                )
                for child in old_children:
                    line.order_id.order_line -= child
                continue

            combo_items = line.product_id.product_tmpl_id.combo_ids.combo_item_ids.filtered(
                lambda item: item.product_id.active
            )
            if not combo_items:
                continue

            line.name = line.product_id.display_name
            line.product_qty = line.product_qty or 1.0
            line.price_unit = 0.0

            # Remove any children previously generated for this parent first.
            old_children = line.order_id.order_line.filtered(
                lambda l: (
                    (l.linked_line_id == line)
                    or (l.linked_virtual_id and l.linked_virtual_id == line.virtual_id)
                )
            )
            for child in old_children:
                line.order_id.order_line -= child

            # Add children without replacing the other PO lines.
            line.order_id.order_line = line.order_id.order_line + self.env[
                'purchase.order.line'
            ].new([
                {
                    'order_id': line.order_id.id,
                    'product_id': item.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom': item.product_id.uom_po_id.id,
                    'price_unit': item.product_id.standard_price,
                    'name': item.product_id.display_name,
                    'combo_item_id': item.id,
                    'linked_virtual_id': line.virtual_id,
                    'sequence': (line.sequence or 10) + index,
                }
                for index, item in enumerate(combo_items, start=1)
            ])

    @api.onchange('product_qty')
    def _onchange_combo_quantity(self):
        for line in self:
            if line.product_id.type != 'combo':
                continue
            children = line.order_id.order_line.filtered(
                lambda l: (
                    (l.linked_line_id == line)
                    or (l.linked_virtual_id and l.linked_virtual_id == line.virtual_id)
                )
            )
            children.product_qty = line.product_qty

    @api.onchange('sequence')
    def _onchange_combo_sequence(self):
        for line in self.filtered(lambda l: l.product_id.type == 'combo'):
            children = line.order_id.order_line.filtered(
                lambda l: (
                    (l.linked_line_id == line)
                    or (l.linked_virtual_id and l.linked_virtual_id == line.virtual_id)
                )
            )
            for index, child in enumerate(children.sorted('sequence'), start=1):
                child.sequence = (line.sequence or 10) + index

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Persist parent/child linkage for combo lines if a combo was created
        # by import/API rather than the form onchange.
        for line in lines.filtered(lambda l: l.product_id.type == 'combo'):
            line._create_combo_components_if_missing()
        return lines

    def _create_combo_components_if_missing(self):
        for line in self:
            if line.combo_item_id:
                continue
            combo_items = line.product_id.product_tmpl_id.combo_ids.combo_item_ids.filtered(
                lambda item: item.product_id.active
            )
            existing = line.linked_line_ids.mapped('combo_item_id')
            for index, item in enumerate(combo_items.filtered(lambda x: x not in existing), start=1):
                self.env['purchase.order.line'].create({
                    'order_id': line.order_id.id,
                    'product_id': item.product_id.id,
                    'product_qty': line.product_qty,
                    'product_uom': item.product_id.uom_po_id.id,
                    'price_unit': item.product_id.standard_price,
                    'name': item.product_id.display_name,
                    'combo_item_id': item.id,
                    'linked_line_id': line.id,
                    'sequence': line.sequence + index,
                })

    def write(self, vals):
        result = super().write(vals)
        if 'product_qty' in vals:
            for line in self.filtered(lambda l: l.product_id.type == 'combo'):
                line.linked_line_ids.write({'product_qty': line.product_qty})
        return result
