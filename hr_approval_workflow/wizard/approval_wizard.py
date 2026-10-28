from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..models.approval_mixin import BUTTON_LABELS


class ApprovalActionWizard(models.TransientModel):
    _name = 'approval.action.wizard'
    _description = 'Approval: choose the records'

    res_model = fields.Char(required=True)
    action_key = fields.Char(required=True)
    line_ids = fields.One2many('approval.action.wizard.line', 'wizard_id', string='Records')
    summary = fields.Char(compute='_compute_summary')

    @api.depends('action_key', 'line_ids.selected')
    def _compute_summary(self):
        for wiz in self:
            label = _(BUTTON_LABELS.get(wiz.action_key, wiz.action_key or ''))
            total = len(wiz.line_ids)
            chosen = len(wiz.line_ids.filtered('selected'))
            wiz.summary = _(
                "%(label)s: these are the ones waiting for you. Untick whoever should stay "
                "as is (%(chosen)s of %(total)s selected).",
                label=label, chosen=chosen, total=total)

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
            raise UserError(_("Select at least one record."))
        records = self.env[self.res_model].browse(ids).exists()
        return records._approval_bulk(self.action_key)


class ApprovalActionWizardLine(models.TransientModel):
    _name = 'approval.action.wizard.line'
    _description = 'Approval: choose the records (line)'
    _order = 'id'

    wizard_id = fields.Many2one('approval.action.wizard', required=True, ondelete='cascade')
    record_id = fields.Integer(required=True)
    selected = fields.Boolean(string='Approve', default=True)
    name = fields.Char(string='Employee / Record')
    extra = fields.Char(string='Details')
    state = fields.Char()
    state_label = fields.Char(string='Current Status')
