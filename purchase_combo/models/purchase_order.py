from odoo import _, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_open_combo_configurator(self):
        """Open the wizard used to add a Combo product (with its choices) to this order."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Add Combo Product"),
            'res_model': 'purchase.combo.configurator',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }
