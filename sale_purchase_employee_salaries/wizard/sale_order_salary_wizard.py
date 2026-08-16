# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderSalaryWizard(models.TransientModel):
    _name = 'sale.order.salary.wizard'
    _description = 'ويزارد توليد بنود المرتبات على أمر البيع'

    order_id = fields.Many2one('sale.order', required=True, readonly=True)
    product_id = fields.Many2one(
        'product.product',
        string='المنتج',
        required=True,
        help='المنتج اللي هيتكرر في بند كل موظف (مثلاً منتج اسمه Salary).',
    )
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='شهر المرتبات (Pay Run)',
        required=True,
    )
    line_ids = fields.One2many(
        'sale.order.salary.wizard.line', 'wizard_id', string='الموظفون'
    )

    def _get_batch_payslips(self):
        self.ensure_one()
        run = self.payslip_run_id
        if 'slip_ids' in run._fields:
            return run.slip_ids
        return self.env['hr.payslip'].search([('payslip_run_id', '=', run.id)])

    @api.onchange('payslip_run_id')
    def _onchange_payslip_run_id(self):
        self.line_ids = [(5, 0, 0)]
        if not self.payslip_run_id:
            return
        payslips = self._get_batch_payslips()
        new_lines = []
        for slip in payslips:
            if not slip.employee_id:
                continue
            amount = slip.employer_cost if 'employer_cost' in slip._fields else slip.net_wage
            new_lines.append((0, 0, {
                'employee_id': slip.employee_id.id,
                'payslip_id': slip.id,
                'amount': amount,
                'to_include': True,
            }))
        self.line_ids = new_lines

    def action_generate_lines(self):
        self.ensure_one()
        SaleOrderLine = self.env['sale.order.line']
        sequence = (max(self.order_id.order_line.mapped('sequence')) + 1) if self.order_id.order_line else 10
        for line in self.line_ids.filtered(lambda l: l.to_include and l.employee_id):
            SaleOrderLine.create({
                'order_id': self.order_id.id,
                'product_id': self.product_id.id,
                'name': f"Salary - {line.employee_id.name}",
                'product_uom_qty': 1,
                'price_unit': line.amount,
                'employee_id': line.employee_id.id,
                'sequence': sequence,
            })
            sequence += 1

        # بنخزّن الباتش على الأوردر نفسه عشان جدول التفاصيل يقدر يتطبع بعد كده
        self.order_id.write({
            'is_salaries': True,
            'payslip_run_id': self.payslip_run_id.id,
        })
        return {'type': 'ir.actions.act_window_close'}


class SaleOrderSalaryWizardLine(models.TransientModel):
    _name = 'sale.order.salary.wizard.line'
    _description = 'سطر موظف في ويزارد المرتبات'

    wizard_id = fields.Many2one('sale.order.salary.wizard', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    payslip_id = fields.Many2one('hr.payslip')
    amount = fields.Monetary(
        string='إجمالي التكلفة',
        currency_field='currency_id',
        help='قابلة للتعديل يدويًا لو الحساب التلقائي مش مطابق. القيمة دي هي price_unit للبند.',
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )
    to_include = fields.Boolean(string='يتضاف؟', default=True)
