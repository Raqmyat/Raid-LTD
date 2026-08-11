# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='الموظف المرتبط بالبند ده (اختياري، ممكن يتستخدم في أي أمر بيع مش بس المرتبات).',
    )
