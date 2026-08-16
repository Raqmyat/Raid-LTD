from odoo import api, models
from odoo.fields import Command


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('order_line')
    def _onchange_combo_order_line(self):
        """Expand combo products immediately in the purchase order UI.

        Odoo Sales uses the purchase/order's one2many onchange to inject the
        combo item lines immediately, instead of waiting for the document to
        be saved. We follow the same pattern here, but use a Section as the
        visible combo header.
        """
        for order in self:
            if not order.order_line:
                continue

            commands = []
            handled_combo_lines = self.env['purchase.order.line']

            # Work on a snapshot because assigning order_line below changes it.
            lines = order.order_line.sorted(key=lambda l: (l.sequence, l.id or 0))

            for line in lines:
                # A combo section already expanded in the current onchange.
                if line.display_type == 'line_section' and line.combo_product_id:
                    handled_combo_lines |= line
                    continue

                if not line.product_id or line.product_id.type != 'combo':
                    continue

                combo_product = line.product_id
                combo_qty = line.product_qty or 1.0
                combo_items = combo_product.product_tmpl_id.combo_ids.combo_item_ids.filtered(
                    lambda item: item.product_id.active
                )

                # Save the combo identity on the section because the section
                # itself cannot legally keep product_id/product_qty values.
                line.combo_product_id = combo_product
                line.combo_qty = combo_qty
                line.display_type = 'line_section'
                line.name = combo_product.display_name
                line.product_id = False
                line.product_qty = 0.0
                line.product_uom_id = False
                line.price_unit = 0.0
                line.date_planned = False
                line.tax_ids = False
                line.discount = 0.0
                handled_combo_lines |= line

                # Remove component lines that may already exist for this combo.
                old_children = order.order_line.filtered(
                    lambda child: (
                        child.combo_item_id
                        and (
                            (line._origin and child.linked_line_id._origin == line._origin)
                            or child.linked_virtual_id == line.virtual_id
                        )
                    )
                )
                commands += [Command.delete(child._origin.id) for child in old_children if child._origin]

                if old_children.filtered(lambda child: not child._origin):
                    order.order_line -= old_children.filtered(lambda child: not child._origin)

                # Shift existing lines so the component rows sit directly below
                # the combo section.
                component_count = len(combo_items)
                if component_count:
                    commands += [
                        Command.update(
                            other.id,
                            {'sequence': other.sequence + component_count},
                        )
                        for other in order.order_line
                        if other != line and other.sequence > line.sequence
                        and other not in old_children
                    ]

                    for index, item in enumerate(combo_items, start=1):
                        product = item.product_id
                        uom = product.uom_id

                        # Prepare the same purchase values Odoo uses for a normal
                        # purchase line (vendor price, taxes, description, etc.).
                        vals = self.env['purchase.order.line']._prepare_purchase_order_line(
                            product_id=product,
                            product_qty=combo_qty,
                            product_uom=uom,
                            company_id=order.company_id.id,
                            partner_id=order.partner_id,
                            po=order,
                        )
                        vals.pop('order_id', None)
                        vals.update({
                            'combo_item_id': item.id,
                            'linked_line_id': line.id if line._origin else False,
                            'linked_virtual_id': line.virtual_id if not line._origin else False,
                            'sequence': line.sequence + index,
                        })
                        commands.append(Command.create(vals))

            if commands:
                order.order_line = commands

