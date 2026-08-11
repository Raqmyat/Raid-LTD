# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    manual_worked_days = fields.Float(
        string='أيام العمل',
        compute='_compute_manual_worked_days',
        inverse='_inverse_manual_worked_days',
        help='عدد أيام العمل الفعلي - بيتقرأ ويتكتب في سطر "Attendance" بتاع Worked Days تلقائي.',
    )

    def _get_main_worked_days_line(self):
        """
        بيرجع سطر "أيام العمل" الأساسي (غالبًا Attendance) من تاب
        Worked Days. لو مفيش سطر بكود واضح، بناخد أول سطر موجود.
        """
        self.ensure_one()
        lines = self.worked_days_line_ids
        if not lines:
            return lines
        attendance_lines = lines.filtered(
            lambda l: l.work_entry_type_id and l.work_entry_type_id.code in (
                'WORK100', 'ATTENDANCE'
            )
        )
        return attendance_lines[:1] or lines[:1]

    @api.depends('worked_days_line_ids.number_of_days')
    def _compute_manual_worked_days(self):
        for slip in self:
            line = slip._get_main_worked_days_line()
            slip.manual_worked_days = line.number_of_days if line else 0.0

    def _inverse_manual_worked_days(self):
        for slip in self:
            line = slip._get_main_worked_days_line()
            if line:
                line.number_of_days = slip.manual_worked_days
