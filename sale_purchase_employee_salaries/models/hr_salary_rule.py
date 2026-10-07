# -*- coding: utf-8 -*-
from odoo import fields, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    profit_account_id = fields.Many2one(
        'account.account',
        string='Revenue Allocation Account',
        company_dependent=True,
        domain="[('account_type', 'in', ['income', 'income_other'])]",
        help='حساب الإيراد/الربحية اللي إجمالي الرول ده (من كل الموظفين) هيتسجل فيه '
             'عند ترحيل فاتورة المرتبات. سيبه فاضي لو الرول مش عايزه يتوزّع.',
    )

    show_in_salary_matrix = fields.Boolean(
        string='Show in Salary Details',
        default=False,
        help='لو متعلّم: الرول ده بيظهر كعمود في جدول تفاصيل المرتبات (المعاينة وطباعة '
             'أمر البيع والفاتورة). سيبه فاضي لو مش عايزه يظهر. '
             'للعرض بس، ومالوش تأثير على إجمالي الفاتورة.',
    )
    include_in_billing_total = fields.Boolean(
        string='Include in Billing Total',
        default=False,
        help='لو متعلّم: قيمة الرول ده بتدخل في إجمالي سطر الموظف (أمر البيع/الفاتورة). '
             'علّم المكوّنات بس، ومتعلّمش رول إجمالي (GROSS/NET) مع مكوّناته عشان ما يتجمعش مرتين. '
             'وتوزيع الإيراد (Revenue Allocation Account) بيشتغل على الرولز دي بس.',
    )
