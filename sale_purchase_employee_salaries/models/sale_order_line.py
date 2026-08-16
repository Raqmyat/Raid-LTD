# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        help='الموظف المرتبط بالبند ده (اختياري، ممكن يتستخدم في أي أمر بيع مش بس المرتبات).',
    )

    def _prepare_invoice_line(self, **optional_values):
        """توريث الموظف تلقائيًا من بند أمر البيع لبند الفاتورة عند الفوترة."""
        vals = super()._prepare_invoice_line(**optional_values)
        if self.employee_id:
            vals['employee_id'] = self.employee_id.id
        return vals
