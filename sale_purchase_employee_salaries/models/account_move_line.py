# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='الموظف المرتبط ببند الفاتورة ده - بيتوّرث تلقائيًا من بند أمر البيع المقابل.',
    )
