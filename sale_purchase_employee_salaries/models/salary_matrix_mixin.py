# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SalaryMatrixMixin(models.AbstractModel):
    _name = 'salary.matrix.mixin'
    _description = 'Provides salary detail matrix data for print & form preview'

    is_salaries = fields.Boolean(string='Is Salaries?')
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Pay Run',
        help='The batch used to build the salary detail columns on print/preview.',
    )
    salary_matrix_preview = fields.Html(
        string='Salary Details',
        compute='_compute_salary_matrix_preview',
    )

    @api.depends('is_salaries', 'payslip_run_id')
    def _compute_salary_matrix_preview(self):
        for rec in self:
            if rec.is_salaries and rec.payslip_run_id:
                rec.salary_matrix_preview = rec._render_salary_matrix_html()
            else:
                rec.salary_matrix_preview = False

    def _get_salary_matrix(self):
        """
        {'columns': [{'code','name'}, ...],
         'rows': [{'employee_id', 'employee', 'values': [...], 'employee_cost'}, ...]}
        كل رولز الرواتب بترتيب ظهورها في تبويب Salary Computation، من غير أي فلترة.
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
                key = rl.code or rl.name
                if key not in seen_codes:
                    seen_codes.add(key)
                    columns.append({'code': key, 'name': rl.name})

        rows = []
        for slip in payslips:
            values_map = {}
            for rl in slip.line_ids:
                key = rl.code or rl.name
                values_map[key] = rl.total
            rows.append({
                'employee_id': slip.employee_id.id,
                'employee': slip.employee_id.name,
                'values': [values_map.get(col['code'], 0.0) for col in columns],
                'employee_cost': slip.employer_cost if 'employer_cost' in slip._fields else 0.0,
            })

        result['columns'] = columns
        result['rows'] = rows
        return result

    def _render_salary_matrix_html(self):
        """نسخة HTML من نفس الجدول، تُعرض في الفورم فيو (تاب Salary Details) قبل الطباعة."""
        self.ensure_one()
        matrix = self._get_salary_matrix()
        if not matrix['columns']:
            return '<p class="text-muted">No payroll data found for the selected Pay Run.</p>'

        th_style = 'border:1px solid #ccc;padding:4px 8px;background:#f1f1f1;'
        td_style = 'border:1px solid #ccc;padding:4px 8px;'
        td_num_style = td_style + 'text-align:right;'

        header_cells = ''.join(
            f'<th style="{th_style}">{col["name"]}</th>' for col in matrix['columns']
        )
        rows_html = ''
        for row in matrix['rows']:
            value_cells = ''.join(
                f'<td style="{td_num_style}">{val:,.2f}</td>' for val in row['values']
            )
            rows_html += (
                f'<tr><td style="{td_style}">{row["employee"]}</td>'
                f'{value_cells}'
                f'<td style="{td_num_style}"><strong>{row["employee_cost"]:,.2f}</strong></td></tr>'
            )

        return (
            '<table style="border-collapse:collapse;width:100%;">'
            '<thead><tr>'
            f'<th style="{th_style}">Employee</th>'
            f'{header_cells}'
            f'<th style="{th_style}">Total Employee Cost</th>'
            '</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            '</table>'
        )
