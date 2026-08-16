from odoo import fields, models


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
