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
        help='المنتج اللي هيتكرر لكل موظف في بنود الأوردر.',
    )
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='شهر المرتبات (Pay Run)',
        required=True,
    )
    line_ids = fields.One2many(
        'sale.order.salary.wizard.line', 'wizard_id', string='الموظفين'
    )

    def _get_batch_payslips(self):
        """
        بيرجع كل الـ payslips المرتبطة بالباتش المختار.
        بنتأكد أوتوماتيك من اسم الحقل اللي بيربط hr.payslip بالباتش، لأنه
        ممكن يكون slip_ids أو payslip_ids حسب النسخة.
        """
        self.ensure_one()
        run = self.payslip_run_id
        for field_name in ('slip_ids', 'payslip_ids'):
            if field_name in run._fields:
                return run[field_name]
        # fallback: نبحث مباشرة في hr.payslip
        if 'payslip_run_id' in self.env['hr.payslip']._fields:
            return self.env['hr.payslip'].search([('payslip_run_id', '=', run.id)])
        return self.env['hr.payslip']

    @api.onchange('payslip_run_id')
    def _onchange_payslip_run_id(self):
        self.line_ids = [(5, 0, 0)]
        if not self.payslip_run_id:
            return
        payslips = self._get_batch_payslips()
        new_lines = []
        for slip in payslips:
            if not slip.employee_id:
                # نتجاهل أي payslip من غير موظف مرتبط (حالة نادرة/بيانات ناقصة)
                continue
            new_lines.append((0, 0, {
                'employee_id': slip.employee_id.id,
                'payslip_id': slip.id,
                'amount': self.env['sale.order.salary.wizard.line']._compute_default_amount(slip),
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
                'name': f"{self.product_id.name} - {line.employee_id.name}",
                'product_uom_qty': 1,
                'price_unit': line.amount,
                'employee_id': line.employee_id.id,
                'sequence': sequence,
            })
            sequence += 1
        return {'type': 'ir.actions.act_window_close'}


class SaleOrderSalaryWizardLine(models.TransientModel):
    _name = 'sale.order.salary.wizard.line'
    _description = 'سطر موظف في ويزارد المرتبات'

    wizard_id = fields.Many2one('sale.order.salary.wizard', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    payslip_id = fields.Many2one('hr.payslip')
    amount = fields.Monetary(
        string='إجمالي المدفوع',
        currency_field='currency_id',
        help='إجمالي التكلفة (مش الصافي بس) - قابل للتعديل يدويًا لو الحساب التلقائي مش مطابق.',
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.company.currency_id
    )
    to_include = fields.Boolean(string='يتضاف؟', default=True)

    @api.model
    def _compute_default_amount(self, payslip):
        """
        بنحاول نجيب "إجمالي التكلفة" مش الصافي بس، بترتيب أولويات:
        1. سطر بكود GROSS لو موجود في هيكل الراتب.
        2. مجموع كل الأسطر ماعدا الخصومات (DEDUCTION) والصافي (NET) نفسه،
           عشان نتجنب double-count.
        3. آخر حل: سطر NET (الصافي) لو مفيش غير كده.
        النتيجة دي مجرد اقتراح مبدئي وقابلة للتعديل يدويًا في الويزارد قبل
        التوليد، لأن مسميات وأكواد بنود الراتب بتختلف حسب هيكل الراتب
        المستخدم عندك.
        """
        lines = getattr(payslip, 'line_ids', payslip.env['hr.payslip.line'])
        if not lines:
            return 0.0

        gross_lines = lines.filtered(lambda l: l.code == 'GROSS')
        if gross_lines:
            return sum(gross_lines.mapped('total'))

        other_lines = lines.filtered(
            lambda l: l.code not in ('NET',)
            and (not l.category_id or l.category_id.code != 'DEDUCTION')
        )
        if other_lines:
            return sum(other_lines.mapped('total'))

        net_lines = lines.filtered(lambda l: l.code == 'NET')
        return sum(net_lines.mapped('total')) if net_lines else 0.0
