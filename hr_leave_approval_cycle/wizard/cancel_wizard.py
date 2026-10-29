from odoo import api, fields, models, _
from odoo.exceptions import UserError


class LeaveApprCancelWizard(models.TransientModel):
    _name = 'leave.appr.cancel.wizard'
    _description = 'Cancel Time Off (Approval Cycle)'

    leave_ids = fields.Many2many('hr.leave', string='Time Off Requests', readonly=True)
    reason = fields.Text(string='Reason', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') != 'hr.leave':
            raise UserError(_("This wizard must be opened from Time Off requests."))
        leaves = self.env['hr.leave'].browse(self.env.context.get('active_ids') or []).exists()
        if not leaves:
            raise UserError(_("No time off request selected."))
        res['leave_ids'] = [(6, 0, leaves.ids)]
        return res

    def action_confirm(self):
        self.ensure_one()
        self.leave_ids._leave_appr_cancel(self.reason)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("%s time off request(s) cancelled.", len(self.leave_ids)),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
