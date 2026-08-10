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

    @api.onchange('company_id')
    def _onchange_company_id_currency(self):
        for rec in self:
            if rec.company_id and not rec.currency_id:
                rec.currency_id = rec.company_id.currency_id
