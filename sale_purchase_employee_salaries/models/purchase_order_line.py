# -*- coding: utf-8 -*-
from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='الموظف المرتبط بالبند ده (اختياري).',
    )
