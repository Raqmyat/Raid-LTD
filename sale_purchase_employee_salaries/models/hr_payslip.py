# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    billing_status = fields.Selection(
        [
            ('none', 'No Sale Order'),
            ('ordered', 'Sale Order - Not Invoiced'),
            ('invoiced', 'Invoiced'),
        ],
        string='Billing Status',
        compute='_compute_billing_status',
        search='_search_billing_status',
        help='حالة الموظف (في نفس الباتش) من ناحية الفوترة:\n'
             '- No Sale Order: مفيش أمر بيع (مرتبات) فيه سطر للموظف ده.\n'
             '- Sale Order - Not Invoiced: متضاف في أمر بيع لسه ما اتعملتلوش فاتورة.\n'
             '- Invoiced: متضاف في فاتورة عملاء (غير ملغية).',
    )

    def _get_salary_detail_lines(self):
        """سطور الرولز المتعلّم عليها Show in Salary Details (للعرض بس)."""
        return self.line_ids.filtered(lambda l: l.salary_rule_id.show_in_salary_matrix)

    def _get_billable_lines(self):
        """سطور الرولز المتعلّم عليها Include in Billing Total (اللي بتتجمع)."""
        return self.line_ids.filtered(lambda l: l.salary_rule_id.include_in_billing_total)

    def _get_billable_amount(self):
        """مجموع الرولز المتعلّم عليها Include in Billing Total = المبلغ اللي بيتفوتر للموظف."""
        self.ensure_one()
        return sum(self._get_billable_lines().mapped('total'))

    @api.model
    def _get_billing_keys(self, slips=None):
        """
        بيرجّع (ordered_keys, invoiced_keys): كل واحد set من (payslip_run_id, employee_id).
        الأوامر/الفواتير الملغية مش بتتحسب. لو slips اتبعتت بنحصر البحث عليها بس.
        """
        so_domain = [
            ('display_type', '=', False),
            ('employee_id', '!=', False),
            ('order_id.is_salaries', '=', True),
            ('order_id.payslip_run_id', '!=', False),
            ('order_id.state', '!=', 'cancel'),
        ]
        inv_domain = [
            ('display_type', '=', 'product'),
            ('is_salary_alloc', '=', False),
            ('employee_id', '!=', False),
            ('move_id.is_salaries', '=', True),
            ('move_id.payslip_run_id', '!=', False),
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '!=', 'cancel'),
        ]
        if slips is not None:
            runs = slips.payslip_run_id.ids
            emps = slips.employee_id.ids
            so_domain += [('employee_id', 'in', emps), ('order_id.payslip_run_id', 'in', runs)]
            inv_domain += [('employee_id', 'in', emps), ('move_id.payslip_run_id', 'in', runs)]

        so_lines = self.env['sale.order.line'].sudo().search(so_domain)
        inv_lines = self.env['account.move.line'].sudo().search(inv_domain)
        ordered = {(l.order_id.payslip_run_id.id, l.employee_id.id) for l in so_lines}
        invoiced = {(l.move_id.payslip_run_id.id, l.employee_id.id) for l in inv_lines}
        return ordered, invoiced

    @staticmethod
    def _status_from_keys(key, ordered, invoiced):
        if key in invoiced:
            return 'invoiced'
        if key in ordered:
            return 'ordered'
        return 'none'

    @api.depends('employee_id', 'payslip_run_id')
    def _compute_billing_status(self):
        ordered, invoiced = self._get_billing_keys(self)
        for slip in self:
            key = (slip.payslip_run_id.id, slip.employee_id.id)
            slip.billing_status = self._status_from_keys(key, ordered, invoiced)

    def _search_billing_status(self, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            raise UserError(self.env._('Unsupported operator for Billing Status.'))
        values = set(value) if isinstance(value, (list, tuple, set)) else {value}

        ordered, invoiced = self._get_billing_keys()
        billed_keys = ordered | invoiced
        run_ids = list({k[0] for k in billed_keys})
        candidates = self.sudo().search([('payslip_run_id', 'in', run_ids)]) if run_ids else self.browse()

        matched_ids, billed_ids = [], []
        for slip in candidates:
            key = (slip.payslip_run_id.id, slip.employee_id.id)
            if key not in billed_keys:
                continue
            billed_ids.append(slip.id)
            if self._status_from_keys(key, ordered, invoiced) in values:
                matched_ids.append(slip.id)

        if 'none' in values:
            domain = ['|', ('id', 'in', matched_ids), ('id', 'not in', billed_ids)]
        else:
            domain = [('id', 'in', matched_ids)]
        if operator in ('!=', 'not in'):
            domain = ['!'] + domain
        return domain
