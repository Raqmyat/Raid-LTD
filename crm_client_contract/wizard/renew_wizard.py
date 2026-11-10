from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class CrmClientContractRenewWizard(models.TransientModel):
    _name = 'crm.client.contract.renew.wizard'
    _description = 'Renew Client Contract'

    contract_id = fields.Many2one('crm.client.contract', required=True, readonly=True, ondelete='cascade')
    date_start = fields.Date(string='New Start Date', compute='_compute_date_start')
    date_end = fields.Date(string='New End Date', required=True)
    currency_id = fields.Many2one(related='contract_id.currency_id')
    fee_amount = fields.Monetary(string='Fee Amount', currency_field='currency_id')
    headcount = fields.Integer(string='Contracted Employees')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        contract = self.env['crm.client.contract'].browse(
            res.get('contract_id') or self.env.context.get('default_contract_id'))
        if contract:
            res.setdefault('date_end', contract._next_term_end())
            res.setdefault('fee_amount', contract.fee_amount)
            res.setdefault('headcount', contract.headcount)
        return res

    @api.depends('contract_id.date_end')
    def _compute_date_start(self):
        for wiz in self:
            wiz.date_start = wiz.contract_id.date_end and wiz.contract_id.date_end + relativedelta(days=1)

    def action_renew(self):
        self.ensure_one()
        new = self.contract_id._renew(self.date_end, fee_amount=self.fee_amount, headcount=self.headcount)
        return {
            'type': 'ir.actions.act_window', 'res_model': 'crm.client.contract',
            'res_id': new.id, 'view_mode': 'form', 'views': [(False, 'form')],
        }
