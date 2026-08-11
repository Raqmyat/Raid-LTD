# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    # سطر يوضّح في الفورم عدد الرواتب اللي لسه مش مدفوعة (اختياري، للعرض فقط)
    custom_unpaid_count = fields.Integer(
        string='رواتب لم تُدفع بعد', compute='_compute_custom_unpaid_count'
    )

    def _compute_custom_unpaid_count(self):
        for run in self:
            run.custom_unpaid_count = len(run.slip_ids.filtered(
                lambda s: not s.move_id or s.move_id.payment_state != 'paid'
            ))

    def write(self, vals):
        res = super().write(vals)
        # =========================================================================
        # مهم جدًا: افتح Developer Mode -> Technical -> Fields على موديل hr.payslip.run
        # وشوف القيم الفعلية لحقل state عندك (draft/verify/close/done/...) وحدّث
        # closing_states بالقيمة الصح اللي بتترحّل لها الحالة بعد الضغط على Validate.
        # =========================================================================
        closing_states = ('close', 'done', 'validated', 'verify')
        if vals.get('state') in closing_states:
            for run in self:
                moves = run.slip_ids.mapped('move_id').filtered(
                    lambda m: m and m.state == 'draft'
                )
                if moves:
                    moves.action_post()
        return res

    def action_open_generate_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('توليد رواتب الباتش'),
            'res_model': 'hr.payslip.run.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payslip_run_id': self.id},
        }

    def action_open_pay_wizard(self):
        self.ensure_one()
        if not self.slip_ids:
            raise UserError(_('لا يوجد رواتب في هذا الباتش لدفعها.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('دفع رواتب الباتش'),
            'res_model': 'hr.payslip.run.pay.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payslip_run_id': self.id},
        }
