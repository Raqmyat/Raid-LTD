# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import Command, models


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'salary.matrix.mixin']

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------
    def _post(self, soft=True):
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

    def _get_move_lines_to_report(self):
        lines = super()._get_move_lines_to_report()
        if self.is_salaries:
            # سطور توزيع الرولز بتتخفي من الطباعة (بتظهر في القيد بس)
            lines = lines.filtered(lambda l: not l.is_salary_alloc)
        return lines

    # ------------------------------------------------------------------
    # Allocation logic
    # ------------------------------------------------------------------
    def _get_slip_cost(self, slip):
        return slip.employer_cost if 'employer_cost' in slip._fields else slip.net_wage

    def _apply_salary_allocation(self):
        """
        بدل ما نضيف سطر مدين، بنخصم قيمة الرولز اللي ليها حساب من سطر كل موظف،
        وبننزلها مرة واحدة: بند واحد لكل رول (مجموعه من كل الموظفين) على حسابه.
        إجمالي الفاتورة والضرايب بيفضلوا زي ما هم.
        """
        self.ensure_one()
        self._remove_salary_allocation_lines()   # يرجّع المبالغ الأصلية لو اتطبّق قبل كده

        run = self.payslip_run_id
        if 'slip_ids' in run._fields:
            slips = run.slip_ids
        else:
            slips = self.env['hr.payslip'].search([('payslip_run_id', '=', run.id)])
        slips_by_emp = defaultdict(lambda: self.env['hr.payslip'])
        for slip in slips:
            slips_by_emp[slip.employee_id.id] |= slip

        currency = self.currency_id
        groups = defaultdict(float)      # (rule, account, taxes) -> amount
        reductions = {}                  # line -> amount
        for line in self.invoice_line_ids.filtered(
                lambda l: l.display_type == 'product' and l.employee_id and not l.is_salary_alloc):
            emp_slips = slips_by_emp.get(line.employee_id.id)
            if not emp_slips:
                continue
            cost = sum(self._get_slip_cost(s) for s in emp_slips)
            if not cost:
                continue
            ratio = line.price_subtotal / cost
            taxes = tuple(sorted(line.tax_ids.ids))
            total = 0.0
            for rl in emp_slips.line_ids:
                rule = rl.salary_rule_id
                account = rule.with_company(self.company_id).profit_account_id
                if not account:
                    continue
                amount = currency.round(rl.total * ratio)
                if currency.is_zero(amount):
                    continue
                groups[(rule, account, taxes)] += amount
                total += amount
            if total:
                reductions[line] = total

        if not groups:
            return False

        commands = []
        for line, amount in reductions.items():
            commands.append(Command.update(line.id, {
                'price_unit': line.price_unit - amount / (line.quantity or 1.0),
                'salary_allocated': amount,
            }))
        sequence = max(self.invoice_line_ids.mapped('sequence') or [10]) + 1
        for (rule, account, taxes), amount in groups.items():
            commands.append(Command.create({
                'display_type': 'product',
                'is_salary_alloc': True,
                'name': rule.name,
                'account_id': account.id,
                'quantity': 1.0,
                'price_unit': currency.round(amount),
                'tax_ids': [Command.set(list(taxes))],
                'sequence': sequence,
            }))
            sequence += 1
        self.write({'invoice_line_ids': commands})
        return True

    def _remove_salary_allocation_lines(self):
        for move in self:
            commands = []
            for line in move.invoice_line_ids:
                if line.is_salary_alloc:
                    commands.append(Command.delete(line.id))
                elif line.salary_allocated:
                    commands.append(Command.update(line.id, {
                        'price_unit': line.price_unit + line.salary_allocated / (line.quantity or 1.0),
                        'salary_allocated': 0.0,
                    }))
            if commands:
                move.write({'invoice_line_ids': commands})
