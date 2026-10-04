# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    salary_reclass_journal_id = fields.Many2one(
        'account.journal',
        string='Salary Allocation Journal',
        domain="[('type', '=', 'general'), ('company_id', '=', id)]",
        help='اليومية اللي هيتسجل فيها قيد توزيع إيراد المرتبات على حسابات الرولز. '
             'لو فاضية بيتاخد أول يومية من نوع Miscellaneous.',
    )
