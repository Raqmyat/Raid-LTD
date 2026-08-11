# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrPayslipRunPayWizard(models.TransientModel):
    _name = 'hr.payslip.run.pay.wizard'
    _description = 'دفع جماعي لرواتب الباتش - سند دفع منفصل لكل موظف'

    payslip_run_id = fields.Many2one('hr.payslip.run', required=True, readonly=True)
    journal_id = fields.Many2one(
        'account.journal', string='يومية الدفع', required=True,
        domain=[('type', 'in', ('bank', 'cash'))],
        help='نفس اليومية هتُستخدم لكل سندات الدفع، لكن هيتعمل سند منفصل لكل Payslip.',
    )
    payment_date = fields.Date(string='تاريخ الدفع', default=fields.Date.context_today, required=True)
    line_ids = fields.One2many(
        'hr.payslip.run.pay.wizard.line', 'wizard_id', string='الرواتب'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        run_id = self.env.context.get('default_payslip_run_id')
        if run_id:
            run = self.env['hr.payslip.run'].browse(run_id)
            payable_slips = run.slip_ids.filtered(
                lambda s: s.move_id and s.move_id.state == 'posted'
                and s.move_id.payment_state != 'paid'
            )
            if not payable_slips:
                raise UserError(_(
                    'لا يوجد رواتب في هذا الباتش جاهزة للدفع (لازم تكون القيود Post أولاً وغير مدفوعة).'
                ))
            res['line_ids'] = [(0, 0, {
                'payslip_id': slip.id,
                'employee_id': slip.employee_id.id,
                'amount': slip.net_wage,
                'to_pay': True,
            }) for slip in payable_slips]
        return res

    def action_select_all(self):
        for wiz in self:
            wiz.line_ids.write({'to_pay': True})
        return self._reopen()

    def action_unselect_all(self):
        for wiz in self:
            wiz.line_ids.write({'to_pay': False})
        return self._reopen()

    def _reopen(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run.pay.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        self.ensure_one()
        lines = self.line_ids.filtered('to_pay')
        if not lines:
            raise UserError(_('اختار راتب واحد على الأقل للدفع.'))
        if not self.journal_id:
            raise UserError(_('اختار يومية الدفع.'))

        paid_slips = self.env['hr.payslip']
        for line in lines:
            slip = line.payslip_id
            move = slip.move_id
            if not move or move.state != 'posted':
                raise UserError(_('راتب %s لازم يكون القيد Post أولاً.') % line.employee_id.name)
            if move.payment_state == 'paid':
                continue  # اتدفع بالفعل، تجاهله

            # سند دفع منفصل لكل Payslip - بالظبط زي الدفع اليدوي لكل واحد لوحده
            payment_register = self.env['account.payment.register'].with_context(
                active_model='account.move',
                active_ids=move.ids,
            ).create({
                'journal_id': self.journal_id.id,
                'payment_date': self.payment_date,
            })
            payment_register._create_payments()
            paid_slips |= slip

        return {
            'type': 'ir.actions.act_window',
            'name': _('الرواتب المدفوعة'),
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('id', 'in', paid_slips.ids)],
        }


class HrPayslipRunPayWizardLine(models.TransientModel):
    _name = 'hr.payslip.run.pay.wizard.line'
    _description = 'سطر دفع راتب داخل ويزارد الدفع الجماعي'

    wizard_id = fields.Many2one('hr.payslip.run.pay.wizard', ondelete='cascade')
    payslip_id = fields.Many2one('hr.payslip', required=True)
    employee_id = fields.Many2one('hr.employee', readonly=True)
    amount = fields.Monetary(string='صافي المرتب', readonly=True)
    currency_id = fields.Many2one(related='payslip_id.currency_id')
    to_pay = fields.Boolean(default=True, string='ادفع')
