# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'salary.matrix.mixin']

    def action_open_salary_wizard(self):
        self.ensure_one()
        return {
            'name': 'توليد بنود المرتبات',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.salary.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_payslip_run_id': self.payslip_run_id.id,
            },
        }

    def _prepare_invoice(self):
        """توريث الباتش وعلامة is_salaries للفاتورة عشان يقدر يطبع نفس جدول التفاصيل."""
        vals = super()._prepare_invoice()
        if self.is_salaries:
            vals['is_salaries'] = True
            vals['payslip_run_id'] = self.payslip_run_id.id
        return vals

    def _create_invoices(self, *args, **kwargs):
        """توزيع الرولز على الحسابات بيتطبّق أول ما الفاتورة تتعمل (Draft)، مش عند التأكيد."""
        invoices = super()._create_invoices(*args, **kwargs)
        for invoice in invoices.filtered(
                lambda m: m.move_type in ('out_invoice', 'out_refund')
                and m.is_salaries and m.payslip_run_id and m.state == 'draft'):
            invoice._apply_salary_allocation()
        return invoices
