from odoo import _, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    client_contract_ids = fields.One2many('crm.client.contract', 'opportunity_id', string='Client Contracts')
    client_contract_count = fields.Integer(compute='_compute_client_contract_count', string='Contracts')

    def _compute_client_contract_count(self):
        data = dict(self.env['crm.client.contract']._read_group(
            [('opportunity_id', 'in', self.ids)], ['opportunity_id'], ['__count']))
        for lead in self:
            lead.client_contract_count = data.get(lead, 0)

    def action_view_client_contracts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('Client Contracts'),
            'res_model': 'crm.client.contract', 'view_mode': 'list,form',
            'domain': [('opportunity_id', '=', self.id)],
            'context': {'default_opportunity_id': self.id,
                        'default_partner_id': self.partner_id.id if self.partner_id.is_company else False,
                        'default_user_id': self.user_id.id or self.env.uid},
        }
