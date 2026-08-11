# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    currency_id = fields.Many2one(
        'res.currency',
        string='عملة راتب الموظف',
        related='current_version_id.currency_id',
        store=True,
        readonly=False,
        domain="[('active', '=', True)]",
    )
    company_currency_id = fields.Many2one(
        related='company_id.currency_id', string='عملة الشركة', readonly=True
    )
    foreign_wage = fields.Monetary(
        string='الراتب بالعملة التانية',
        related='current_version_id.foreign_wage',
        store=True,
        readonly=False,
        currency_field='currency_id',
    )
