# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    actual_input_note = fields.Char(
        string='Actual Inputs Status',
        compute='_compute_actual_input_note',
        help='بيوضح هل فيه صفوف Actual Salary Inputs لنفس الموظف والشهر ده '
             'هتتضاف تلقائيًا لتبويب Other Inputs لما تدوس Compute Sheet.',
    )

    @api.depends('employee_id', 'date_from')
    def _compute_actual_input_note(self):
        for slip in self:
            recs = slip._get_actual_input_records()
            if recs:
                names = ', '.join(recs.mapped('input_type_id.name'))
                slip.actual_input_note = 'هيتضاف: %s' % names
            else:
                slip.actual_input_note = ''

    def _get_actual_input_records(self):
        """رجّع كل صفوف Actual Salary Inputs بتاعة نفس الموظف ونفس شهر
        الـ Payslip ده (بغض النظر عن نوع الـ Input)."""
        self.ensure_one()
        if not self.employee_id or not self.date_from:
            return self.env['hr.payslip.actual.input']
        return self.env['hr.payslip.actual.input'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '=', self.date_from.replace(day=1)),
        ])

    def compute_sheet(self):
        for slip in self:
            slip._sync_actual_inputs_to_payslip()
        return super().compute_sheet()

    def _sync_actual_inputs_to_payslip(self):
        """بتضخّ كل صف من جدول Actual Salary Inputs (hr.payslip.actual.input)
        الخاص بنفس الموظف ونفس الشهر جوه Other Inputs الحقيقية للـ Payslip
        (hr.payslip.input)، عشان أي Salary Rule يقدر يستخدمها عادي بـ
        inputs.CODE.amount من غير أي كود بحث مخصص.
        لو فيه سطر بنفس الـ Input Type موجود قبل كده في نفس الـ Payslip،
        بس بيتحدث الـ Amount بتاعه، مش بيتكرر.
        """
        self.ensure_one()
        actual_inputs = self._get_actual_input_records()
        for rec in actual_inputs:
            line = self.input_line_ids.filtered(
                lambda l: l.input_type_id == rec.input_type_id)
            if line:
                line[0].amount = rec.amount
            else:
                self.env['hr.payslip.input'].create({
                    'payslip_id': self.id,
                    'input_type_id': rec.input_type_id.id,
                    'amount': rec.amount,
                    'name': rec.note or rec.input_type_id.name,
                })
