# -*- coding: utf-8 -*-
from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    currency_id = fields.Many2one(
        'res.currency',
        string='عملة راتب الموظف',
        related=None,
        compute=None,
        store=True,
        readonly=False,
        default=lambda self: self.env.company.currency_id,
        domain="[('active', '=', True)]",
        help='لو سبتها زي عملة الشركة، مفيش أي تأثير خالص.',
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id', string='عملة الشركة', readonly=True
    )
    foreign_wage = fields.Monetary(
        string='الراتب بالعملة التانية',
        currency_field='currency_id',
        help=(
            'راتب الموظف بعملته (زي دولار مثلاً). القيمة دي بتتقرأ تلقائي '
            'وقت عمل أي Payslip له، وبيتعمل منها Override لحقل الراتب '
            'الأساسي (Wage) بعملة الشركة وقت الضغط على Compute Sheet.'
        ),
    )
