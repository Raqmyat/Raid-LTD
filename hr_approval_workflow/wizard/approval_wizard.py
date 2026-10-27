import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from ..models.approval_mixin import APPROVAL_SEQUENCE, APPROVAL_STATES, FINAL_STATES

ACTION_TYPES = [
    ('next', 'Next step (Submit / Operations approve / HR approve)'),
    ('send_finance', 'Send to Finance'),
    ('send_ceo', 'Send to CEO'),
    ('close', 'Close & Post'),
    ('refuse', 'Refuse'),
    ('reset', 'Reset refused records'),
]

# Which actions are possible from each status
ALLOWED_ACTIONS = {
    'draft': ['next'],
    'submitted': ['next', 'refuse'],
    'ops_approved': ['next', 'refuse'],
    'hr_approved': ['send_finance', 'close', 'refuse'],
    'finance': ['send_ceo', 'close', 'refuse'],
    'ceo': ['close', 'refuse'],
    'refused': ['reset'],
}
NEXT_METHOD = {
    'draft': 'action_approval_submit',
    'submitted': 'action_approval_ops_approve',
    'ops_approved': 'action_approval_hr_approve',
}
METHOD = {
    'send_finance': 'action_approval_send_finance',
    'send_ceo': 'action_approval_send_ceo',
    'close': 'action_approval_close',
    'refuse': 'action_approval_refuse',
    'reset': 'action_approval_reset',
}


class BulkApprovalWizard(models.TransientModel):
    _name = 'bulk.approval.wizard'
    _description = 'Bulk Approval'

    res_model = fields.Char(required=True)
    res_ids = fields.Text(required=True)
    lowest_state = fields.Selection(APPROVAL_STATES, string='Status to process', readonly=True)
    action_type = fields.Selection(ACTION_TYPES, string='Action', required=True, default='next')
    allowed_hint = fields.Char(string='Available actions', readonly=True)
    breakdown = fields.Text(string='Selection breakdown', readonly=True)
    record_count = fields.Integer(string='To process', readonly=True)
    skipped_count = fields.Integer(string='Skipped (ahead / finished)', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        model = self.env.context.get('active_model')
        ids = self.env.context.get('active_ids') or []
        if not model or 'approval_state' not in self.env[model]._fields:
            raise UserError(_("This action is not available for this model."))
        records = self.env[model].browse(ids).exists()
        if not records:
            raise UserError(_("No records selected."))

        in_progress = records.filtered(lambda r: r.approval_state not in FINAL_STATES)
        if in_progress:
            lowest = min(in_progress.mapped('approval_state'),
                         key=lambda s: APPROVAL_SEQUENCE[s])
        elif all(r.approval_state == 'refused' for r in records):
            lowest = 'refused'
        else:
            raise UserError(_("All selected records are already closed."))
        target = records.filtered(lambda r: r.approval_state == lowest)

        labels = dict(APPROVAL_STATES)
        counts = {}
        for state in records.mapped('approval_state'):
            counts[state] = counts.get(state, 0) + 1
        breakdown = '\n'.join(
            f"{labels[s]}: {counts[s]}"
            for s in sorted(counts, key=lambda s: APPROVAL_SEQUENCE[s]))
        action_labels = dict(ACTION_TYPES)
        allowed = ALLOWED_ACTIONS[lowest]

        res.update({
            'res_model': model,
            'res_ids': json.dumps(target.ids),
            'lowest_state': lowest,
            'action_type': allowed[0],
            'allowed_hint': ' / '.join(action_labels[a] for a in allowed),
            'breakdown': breakdown,
            'record_count': len(target),
            'skipped_count': len(records) - len(target),
        })
        return res

    def action_confirm(self):
        self.ensure_one()
        records = self.env[self.res_model].browse(json.loads(self.res_ids)).exists()
        # re-filter: someone may have changed the status meanwhile
        records = records.filtered(lambda r: r.approval_state == self.lowest_state)
        if not records:
            raise UserError(_("Nothing to process: the status of the records has changed."))
        if self.action_type not in ALLOWED_ACTIONS[self.lowest_state]:
            raise UserError(_(
                "Action '%(action)s' is not possible for records in status '%(state)s'. "
                "Available: %(allowed)s",
                action=dict(ACTION_TYPES)[self.action_type],
                state=dict(APPROVAL_STATES)[self.lowest_state],
                allowed=self.allowed_hint))

        if self.action_type == 'next':
            method = NEXT_METHOD[self.lowest_state]
        else:
            method = METHOD[self.action_type]
        getattr(records, method)()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'title': _("Approval"),
                'message': _(
                    "%(done)s record(s) processed, %(skipped)s skipped.",
                    done=len(records), skipped=self.skipped_count),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
