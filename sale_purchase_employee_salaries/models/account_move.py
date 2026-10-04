# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import Command, fields, models, _


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'salary.matrix.mixin']

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------
    def _post(self, soft=True):
        # بنضيف سطور التوزيع جوه قيد الفاتورة نفسه قبل الترحيل
        for move in self:
            if (move.state == 'draft'
                    and move.move_type in ('out_invoice', 'out_refund')
                    and move.is_salaries and move.payslip_run_id):
                move._apply_salary_allocation()
        return super()._post(soft=soft)

    def button_draft(self):
        res = super().button_draft()
        self.filtered(lambda m: m.state == 'draft')._remove_salary_allocation_lines()
        return res

    # ------------------------------------------------------------------
    # Allocation logic
    # ------------------------------------------------------------------
    def _get_slip_cost(self, slip):
        return slip.employer_cost if 'employer_cost' in slip._fields else slip.net_wage

    def _compute_salary_allocation(self):
        """
        {(rule, rule_account, source_account): amount} بعملة الشركة، بإشارة موجبة.
        لكل بند موظف: نسبة = قيمة البند / تكلفة الموظف في الـ payslip،
        وكل رول له حساب بيتضرب قيمته في النسبة دي. اللي مش متوزّع بيفضل في حساب المنتج.
        """
        self.ensure_one()
        run = self.payslip_run_id
        if 'slip_ids' in run._fields:
            slips = run.slip_ids
        else:
            slips = self.env['hr.payslip'].search([('payslip_run_id', '=', run.id)])

        slips_by_emp = defaultdict(lambda: self.env['hr.payslip'])
        for slip in slips:
            slips_by_emp[slip.employee_id.id] |= slip

        allocation = defaultdict(float)
        lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type == 'product' and l.employee_id
        )
        for line in lines:
            emp_slips = slips_by_emp.get(line.employee_id.id)
            if not emp_slips:
                continue
            cost = sum(self._get_slip_cost(s) for s in emp_slips)
            if not cost:
                continue
            factor = -line.balance / cost  # الفاتورة: balance سالب -> نسبة موجبة
            for rl in emp_slips.line_ids:
                rule = rl.salary_rule_id
                account = rule.with_company(self.company_id).profit_account_id
                if not account:
                    continue
                allocation[(rule, account, line.account_id)] += rl.total * factor
        return allocation

    def _salary_alloc_line_cmd(self, account, balance, name):
        company_currency = self.company_id.currency_id
        date = self.invoice_date or fields.Date.context_today(self)
        return Command.create({
            'display_type': 'cogs',        # سطر محاسبي بس: مش بيدخل في الإجمالي ولا بيظهر في بنود الفاتورة
            'is_salary_alloc': True,
            'account_id': account.id,
            'name': name,
            'partner_id': self.partner_id.id,
            'currency_id': self.currency_id.id,
            'amount_currency': company_currency._convert(
                balance, self.currency_id, self.company_id, date),
            'balance': balance,
        })

    def _apply_salary_allocation(self):
        self.ensure_one()
        self._remove_salary_allocation_lines()
        allocation = self._compute_salary_allocation()
        if not allocation:
            return False

        currency = self.company_id.currency_id
        credits = defaultdict(float)   # (rule, account) -> amount
        debits = defaultdict(float)    # source account -> amount
        for (rule, account, source), amount in allocation.items():
            amount = currency.round(amount)
            if currency.is_zero(amount):
                continue
            credits[(rule, account)] += amount
            debits[source] += amount
        if not credits:
            return False

        commands = []
        for (rule, account), amount in credits.items():
            # سطر واحد لكل رول = مجموع الرول من كل الموظفين (دائن على حساب الربح)
            commands.append(self._salary_alloc_line_cmd(
                account, -currency.round(amount), rule.name))
        for source, amount in debits.items():
            # مدين على حساب المنتج الأصلي عشان الإيراد ميتحسبش مرتين
            commands.append(self._salary_alloc_line_cmd(
                source, currency.round(amount), _('Salary allocation')))
        self.write({'line_ids': commands})
        return True

    def _remove_salary_allocation_lines(self):
        for move in self:
            move.line_ids.filtered('is_salary_alloc').unlink()
