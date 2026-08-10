# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrVersion(models.Model):
    # في أودو 19: hr.contract اتلغى وبقى hr.version (الجدول hr_contract بقى hr_version).
    # الموديل ده هو اللي بيمثل "نسخة" بيانات الموظف (الراتب والعقد) اللي بتظهر
    # جوه تاب Payroll في كارت الموظف نفسه.
    _inherit = 'hr.version'

    currency_id = fields.Many2one(
        'res.currency',
        string='Salary Currency',
        default=lambda self: self.env.company.currency_id,
        help='العملة اللي هيتحسب بيها راتب هذا الموظف/هذه النسخة (ممكن تختلف عن عملة الشركة).',
    )

    # ⚠️ الجزء الأهم: حقل wage الأصلي معرّف في الأودو بحيث ياخد عملته من
    # عملة الشركة (currency_field على الأرجح = 'company_currency_id' أو
    # مشتق منها). إعادة تعريفه هنا بـ currency_field='currency_id' بتخلي
    # أودو يعرض ويحسب المبلغ بعملة النسخة اللي احنا ضايفينها، مش عملة الشركة.
    # نفس الفكرة تنطبق على أي حقل Monetary تاني مرتبط بالراتب لو موجود عندك
    # (مثلاً hourly_wage لو الأجر بالساعة).
    wage = fields.Monetary(currency_field='currency_id')

    @api.onchange('company_id')
    def _onchange_company_id_currency(self):
        for rec in self:
            if rec.company_id and not rec.currency_id:
                rec.currency_id = rec.company_id.currency_id
