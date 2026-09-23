# -*- coding: utf-8 -*-
from odoo import api, fields, models

ACTUAL_BASIC_CODE = 'ACTUALBASIC'


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    actual_basic_amount = fields.Float(
        string='Actual Basic',
        compute='_compute_actual_basic_amount',
        inverse='_inverse_actual_basic_amount',
        help='القيمة الفعلية للراتب الأساسي للشهر ده. بتتقرأ وبتتكتب '
             'مباشرة في جدول Actual Salary Inputs (موديل '
             'hr.payslip.actual.input) لنفس الموظف ونفس الشهر، فمش '
             'بتتأثر بعمل Compute Sheet.',
    )

    def _get_actual_basic_input_type(self):
        return self.env['hr.payslip.input.type'].search(
            [('code', '=', ACTUAL_BASIC_CODE)], limit=1)

    def _get_actual_basic_record(self):
        self.ensure_one()
        if not self.employee_id or not self.date_from:
            return self.env['hr.payslip.actual.input']
        input_type = self._get_actual_basic_input_type()
        if not input_type:
            return self.env['hr.payslip.actual.input']
        return self.env['hr.payslip.actual.input'].search([
            ('employee_id', '=', self.employee_id.id),
            ('input_type_id', '=', input_type.id),
            ('date_from', '=', self.date_from.replace(day=1)),
        ], limit=1)

    @api.depends('employee_id', 'date_from')
    def _compute_actual_basic_amount(self):
        for slip in self:
            rec = slip._get_actual_basic_record()
            slip.actual_basic_amount = rec.amount if rec else 0.0

    def _inverse_actual_basic_amount(self):
        input_type = self._get_actual_basic_input_type()
        if not input_type:
            input_type = self.env['hr.payslip.input.type'].create({
                'name': 'Actual Basic',
                'code': ACTUAL_BASIC_CODE,
            })
        for slip in self:
            if not slip.employee_id or not slip.date_from:
                continue
            rec = slip._get_actual_basic_record()
            if rec:
                rec.amount = slip.actual_basic_amount
            else:
                self.env['hr.payslip.actual.input'].create({
                    'employee_id': slip.employee_id.id,
                    'input_type_id': input_type.id,
                    'date_from': slip.date_from.replace(day=1),
                    'amount': slip.actual_basic_amount,
                })
