# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    currency_id = fields.Many2one(
        'res.currency',
        string='عملة راتب الموظف',
        compute='_compute_salary_currency_fields',
        readonly=True,
    )
    foreign_wage = fields.Monetary(
        string='الراتب المسجل بالعملة التانية',
        currency_field='currency_id',
        compute='_compute_salary_currency_fields',
        readonly=True,
        help='القيمة دي بتتقرأ تلقائي من كارت الموظف، للعرض بس (مش قابلة للتعديل من هنا).',
    )

    def _get_version(self):
        """
        بيرجع الـ hr.version (العقد سابقًا) المرتبط بالـ payslip. بنتأكد
        أوتوماتيك من اسم الحقل لأنه ممكن يكون contract_id أو version_id.
        """
        self.ensure_one()
        if 'version_id' in self._fields and self.version_id:
            return self.version_id
        if 'contract_id' in self._fields and self.contract_id:
            return self.contract_id
        return self.env['hr.version']

    @api.depends('employee_id')
    def _compute_salary_currency_fields(self):
        for slip in self:
            version = slip._get_version()
            if version and version.currency_id:
                slip.currency_id = version.currency_id
                slip.foreign_wage = version.foreign_wage
            else:
                slip.currency_id = slip.company_id.currency_id
                slip.foreign_wage = 0.0

    def _apply_foreign_wage_override(self):
        """
        بتقرأ الراتب بالعملة التانية من كارت الموظف، وتحوّله وتحطه في
        حقل wage الأساسي (بعملة الشركة) قبل ما البايرول يحسب.
        """
        for slip in self:
            version = slip._get_version()
            if not version or not version.currency_id or not slip.company_id:
                continue
            if version.currency_id == slip.company_id.currency_id:
                # نفس عملة الشركة: مفيش أي override.
                continue
            if not version.foreign_wage:
                continue
            date = slip.date_from or fields.Date.context_today(slip)
            converted = version.currency_id._convert(
                version.foreign_wage,
                slip.company_id.currency_id,
                slip.company_id,
                date,
            )
            version.write({'wage': converted})

    def compute_sheet(self):
        """
        قبل ما نحسب البايرول، بنعمل Override لحقل wage من القيمة المسجلة
        بعملة الموظف. لو اسم الميثود دي مختلف عندك (زي action_compute_sheet
        بدل compute_sheet)، خلي بالك تظبطها.
        """
        self._apply_foreign_wage_override()
        return super().compute_sheet()
