# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrPayslipRunGenerateWizard(models.TransientModel):
    _name = 'hr.payslip.run.generate.wizard'
    _description = 'توليد رواتب الباتش بتحديد أيام العمل يدويًا (بدون جهاز بصمة)'

    payslip_run_id = fields.Many2one('hr.payslip.run', required=True, readonly=True)
    structure_id = fields.Many2one('hr.payroll.structure', string='هيكل الراتب')
    department_id = fields.Many2one('hr.department', string='القسم (للفلترة فقط)')
    line_ids = fields.One2many(
        'hr.payslip.run.generate.wizard.line', 'wizard_id', string='الموظفون'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        run_id = self.env.context.get('default_payslip_run_id')
        if run_id:
            employees = self.env['hr.employee'].search([('contract_id', '!=', False)])
            res['line_ids'] = [(0, 0, {
                'employee_id': emp.id,
                'days_worked': 30.0,
            }) for emp in employees]
        return res

    def action_load_employees(self):
        """إعادة تحميل قائمة الموظفين حسب القسم المختار (اختياري)."""
        self.ensure_one()
        domain = [('contract_id', '!=', False)]
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        employees = self.env['hr.employee'].search(domain)
        self.line_ids = [(5, 0, 0)] + [(0, 0, {
            'employee_id': emp.id,
            'days_worked': 30.0,
        }) for emp in employees]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip.run.generate.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        self.ensure_one()
        Payslip = self.env['hr.payslip']
        selected_lines = self.line_ids.filtered('selected')
        if not selected_lines:
            raise UserError(_('اختار موظف واحد على الأقل.'))

        created = Payslip
        for line in selected_lines:
            employee = line.employee_id
            contract = employee.contract_id
            if not contract:
                raise UserError(_('الموظف %s ليس له عقد سارٍ.') % employee.name)
            if line.days_worked <= 0:
                raise UserError(_('عدد أيام العمل للموظف %s يجب أن يكون أكبر من صفر.') % employee.name)

            struct_id = self.structure_id.id
            if not struct_id and contract.structure_type_id:
                struct_id = contract.structure_type_id.default_struct_id.id

            slip = Payslip.create({
                'employee_id': employee.id,
                'contract_id': contract.id,
                'name': _('راتب - %s') % employee.name,
                'date_from': self.payslip_run_id.date_start,
                'date_to': self.payslip_run_id.date_end,
                'struct_id': struct_id,
                'payslip_run_id': self.payslip_run_id.id,
            })

            # عدّل الكود ده ليطابق كود نوع الحضور (Work Entry Type) المستخدم في هيكل الراتب عندك
            work_entry_type = self.env['hr.work.entry.type'].search(
                [('code', '=', 'WORK100')], limit=1
            )
            hours_per_day = contract.resource_calendar_id.hours_per_day or 8.0

            if work_entry_type and 'worked_days_line_ids' in slip._fields:
                slip.worked_days_line_ids = [(5, 0, 0), (0, 0, {
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_days': line.days_worked,
                    'number_of_hours': line.days_worked * hours_per_day,
                })]

            if hasattr(slip, 'compute_sheet'):
                slip.compute_sheet()
            created |= slip

        return {
            'type': 'ir.actions.act_window',
            'name': _('الرواتب المولّدة'),
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
        }


class HrPayslipRunGenerateWizardLine(models.TransientModel):
    _name = 'hr.payslip.run.generate.wizard.line'
    _description = 'سطر أيام عمل الموظف داخل ويزارد التوليد'

    wizard_id = fields.Many2one('hr.payslip.run.generate.wizard', ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    department_id = fields.Many2one(related='employee_id.department_id', readonly=True)
    selected = fields.Boolean(default=True, string='تضمين')
    days_worked = fields.Float(string='أيام العمل', default=30.0, required=True)
