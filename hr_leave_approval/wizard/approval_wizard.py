from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..models.hr_leave import BUTTON_LABELS


class HrLeaveApprovalWizard(models.TransientModel):
    _name = 'hr.leave.approval.wizard'
    _description = 'Time Off approval: choose the requests'

    action_key = fields.Char(required=True)
    line_ids = fields.One2many('hr.leave.approval.wizard.line', 'wizard_id', string='Requests')
    summary = fields.Char(compute='_compute_summary')

    @api.depends('action_key', 'line_ids.selected')
    def _compute_summary(self):
        for wiz in self:
            label = _(BUTTON_LABELS.get(wiz.action_key, wiz.action_key or ''))
            wiz.summary = _(
                "%(label)s: these requests are waiting for you. Untick whoever should stay "
                "as is (%(chosen)s of %(total)s selected).",
                label=label, chosen=len(wiz.line_ids.filtered('selected')), total=len(wiz.line_ids))

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _(BUTTON_LABELS.get(self.action_key, 'Approval')),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_select_all(self):
        self.line_ids.write({'selected': True})
        return self._reopen()

    def action_unselect_all(self):
        self.line_ids.write({'selected': False})
        return self._reopen()

    def action_confirm(self):
        self.ensure_one()
        ids = self.line_ids.filtered('selected').mapped('record_id')
        if not ids:
            raise UserError(_("Select at least one request."))
        leaves = self.env['hr.leave'].sudo().browse(ids).exists()
        return leaves._lv_bulk(self.action_key)


class HrLeaveApprovalWizardLine(models.TransientModel):
    _name = 'hr.leave.approval.wizard.line'
    _description = 'Time Off approval: choose the requests (line)'
    _order = 'id'

    wizard_id = fields.Many2one('hr.leave.approval.wizard', required=True, ondelete='cascade')
    record_id = fields.Integer(required=True)
    selected = fields.Boolean(string='Approve', default=True)
    name = fields.Char(string='Employee')
    extra = fields.Char(string='Details')
    state_label = fields.Char(string='Current Status')
