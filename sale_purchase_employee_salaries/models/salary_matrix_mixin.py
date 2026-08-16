# -*- coding: utf-8 -*-
from odoo import fields, models


class SalaryMatrixMixin(models.AbstractModel):
    """
    Mixin مشترك بين sale.order و account.move: بيوفر حقل الربط بباتش
    الرواتب (Pay Run) وميثود بناء جدول التفصيل (Employee x Rule) اللي
    بيتطبع في التقرير بس، ومش بيتحول لبنود فعلية في الأوردر/الفاتورة.
    """
    _name = 'salary.matrix.mixin'
    _description = 'يوفر بيانات جدول تفصيل الرواتب للطباعة'

    is_salaries = fields.Boolean(string='Is Salaries?')
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='شهر المرتبات (Pay Run)',
        help='الباتش اللي اتولدت منه بنود المرتبات - بيُستخدم لبناء جدول التفاصيل عند الطباعة.',
    )

    def _get_salary_matrix(self):
        """
        بيرجع dict: {'columns': [{'code','name'}, ...], 'rows': [{'employee','values':[...], 'employee_cost'}, ...]}
        الأعمدة بتتبني ديناميكيًا من كل رولز الرواتب (appears_on_payslip فقط لو الحقل موجود)
        الظاهرة فعليًا في قسائم الباتش، بترتيب أول ظهور.
        """
        self.ensure_one()
        result = {'columns': [], 'rows': []}
        run = self.payslip_run_id
        if not run:
            return result

        if 'slip_ids' in run._fields:
            payslips = run.slip_ids
        else:
            payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', run.id)])

        columns = []
        seen_codes = set()
        for slip in payslips:
            for rl in slip.line_ids:
                if 'appears_on_payslip' in rl._fields and not rl.appears_on_payslip:
                    continue
                key = rl.code or rl.name
                if key not in seen_codes:
                    seen_codes.add(key)
                    columns.append({'code': key, 'name': rl.name})

        rows = []
        for slip in payslips:
            values_map = {}
            for rl in slip.line_ids:
                if 'appears_on_payslip' in rl._fields and not rl.appears_on_payslip:
                    continue
                key = rl.code or rl.name
                values_map[key] = rl.total
            rows.append({
                'employee': slip.employee_id.name,
                'values': [values_map.get(col['code'], 0.0) for col in columns],
                'employee_cost': slip.employer_cost if 'employer_cost' in slip._fields else 0.0,
            })

        result['columns'] = columns
        result['rows'] = rows
        return result
