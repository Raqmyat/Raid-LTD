from odoo import api, models
from odoo.fields import Command


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.onchange('order_line')
    def _onchange_combo_order_line(self):
        """Expand combo products immediately in the purchase order UI.

        A combo becomes a real Section and its items are inserted as normal
        purchase lines immediately, without waiting for Save. The employee
        selected on the purchase order is copied to every combo component.
        """
        for order in self:
            if not order.order_line:
                continue

            commands = []
            lines = order.order_line.sorted(key=lambda l: (l.sequence, l.id or 0))
            for line in lines:
                if line.display_type == 'line_section' and line.combo_product_id:
                    employee = line.employee_id if 'employee_id' in line._fields else False
                    if employee and 'employee_id' in line.linked_line_ids._fields:
                        line.linked_line_ids.employee_id = employee
                    if employee:
                        line.name = f"{line.combo_product_id.display_name} - {employee.name}"
                    continue

                if not line.product_id or line.product_id.type != 'combo':
                    continue

                # Employee belongs to the purchase order line in the user's
                # customization. Capture it BEFORE changing the combo line into
                # a section, because the section itself is non-accountable.
                employee = line.employee_id if 'employee_id' in line._fields else False

                if not employee:
                    return {
                        'warning': {
                            'title': 'Employee Required',
                            'message': 'Please select an Employee on the Combo line before selecting the Combo product.',
                        }
                    }

                combo_product = line.product_id
                combo_qty = line.product_qty or 1.0
                combo_items = combo_product.product_tmpl_id.combo_ids.combo_item_ids.filtered(
                    lambda item: item.product_id.active
                )

                line.combo_product_id = combo_product
                line.combo_qty = combo_qty
                line.display_type = 'line_section'
                line.name = f"{combo_product.display_name} - {employee.name}"
                line.product_id = False
                line.product_qty = 0.0
                line.product_uom_id = False
                line.price_unit = 0.0
                line.date_planned = False
                line.tax_ids = False
                line.discount = 0.0
                if 'employee_id' in line._fields:
                    line.employee_id = False

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

                unsaved_old_children = old_children.filtered(lambda child: not child._origin)
                if unsaved_old_children:
                    order.order_line -= unsaved_old_children

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
                        and other.id
                    ]

                    for index, item in enumerate(combo_items, start=1):
                        product = item.product_id
                        uom = product.uom_id
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
                        if 'employee_id' in self.env['purchase.order.line']._fields:
                            vals['employee_id'] = employee.id
                        commands.append(Command.create(vals))

            if commands:
                order.order_line = commands
