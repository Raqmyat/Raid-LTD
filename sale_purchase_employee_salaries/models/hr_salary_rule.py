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
