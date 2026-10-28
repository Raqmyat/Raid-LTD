import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

MODULE = 'hr_approval_workflow'
ROLES = [
    ('submit', 'Submitter'),
    ('ops', 'Operations'),
    ('hr', 'HR'),
    ('finance', 'Finance'),
    ('ceo', 'CEO'),
]
DEFAULT_GROUPS = {
    'submit': f'{MODULE}.group_approval_submitter',
    'ops': f'{MODULE}.group_approval_ops',
    'hr': f'{MODULE}.group_approval_hr',
    'finance': f'{MODULE}.group_approval_finance',
    'ceo': f'{MODULE}.group_approval_ceo',
}


class ApprovalStep(models.Model):
    """One row per (model, role): which group may act for that role and
    whether its members get a notification when something waits for them."""
    _name = 'approval.step'
    _description = 'Approval Role Configuration'
    _order = 'res_model, sequence, id'

    name = fields.Char(required=True)
    res_model = fields.Char(string='Model', required=True, default='hr.payslip', readonly=True)
    role = fields.Selection(ROLES, required=True, readonly=True)
    group_id = fields.Many2one(
        'res.groups', string='Allowed Group', required=True, ondelete='restrict',
        help="Members of this group can act for this role (buttons are shown to them "
             "and the server checks it). Pick any existing group.")
    group_xmlid = fields.Char(compute='_compute_group_xmlid', store=True)
    notify = fields.Boolean(
        string='Notify', default=True,
        help="Notify the members of the group when a record is waiting for them.")
    sequence = fields.Integer(default=10)

    @api.constrains('res_model', 'role')
    def _check_unique_role(self):
        for rec in self:
            if self.search_count([('res_model', '=', rec.res_model), ('role', '=', rec.role)]) > 1:
                raise ValidationError(_("This role is already configured for %s.", rec.res_model))

    @api.depends('group_id')
    def _compute_group_xmlid(self):
        """has_group() and the `groups` attribute of views need an external id;
        groups created from the UI get one (in __export__, never cleaned up)."""
        Data = self.env['ir.model.data'].sudo()
        for step in self:
            group = step.group_id
            if not group:
                step.group_xmlid = False
                continue
            data = Data.search([('model', '=', 'res.groups'), ('res_id', '=', group.id)], limit=1)
            if not data:
                data = Data.create({
                    'module': '__export__',
                    'name': 'res_groups_%s_approval' % group.id,
                    'model': 'res.groups',
                    'res_id': group.id,
                    'noupdate': True,
                })
            step.group_xmlid = '%s.%s' % (data.module, data.name)

    # the views are built from this configuration -> refresh their cache
    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self.env.registry.clear_cache()
        return res

    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    # ------------------------------------------------------------------
    @api.model
    def _get_step(self, res_model, role):
        return self.sudo().search([('res_model', '=', res_model), ('role', '=', role)], limit=1)

    @api.model
    def _group_xmlid_for(self, res_model, role):
        step = self._get_step(res_model, role)
        return step.group_xmlid or DEFAULT_GROUPS.get(role)

    def _get_users(self):
        self.ensure_one()
        group = self.group_id.sudo()
        users = group['user_ids'] if 'user_ids' in group._fields else group['users']
        return users.filtered(lambda u: u.active and not u.share)
