# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='الموظف المرتبط ببند الفاتورة ده - بيتوّرث تلقائيًا من بند أمر البيع المقابل.',
    )
    is_salary_alloc = fields.Boolean(
        string='Salary Allocation Line',
        help='بند توزيع رول على حساب الربح (بيتولّد تلقائي عند الترحيل ويتشال لو رجّعت Draft).',
    )
    salary_allocated = fields.Monetary(
        string='Allocated to Rules',
        currency_field='currency_id',
        help='المبلغ اللي اتخصم من البند ده ونزل على حسابات الرولز.',
    )
    salary_gross_subtotal = fields.Monetary(
        string='Gross Subtotal',
        currency_field='currency_id',
        compute='_compute_salary_gross_subtotal',
    )

    @api.depends('price_subtotal', 'salary_allocated')
    def _compute_salary_gross_subtotal(self):
        for line in self:
            line.salary_gross_subtotal = line.price_subtotal + line.salary_allocated
