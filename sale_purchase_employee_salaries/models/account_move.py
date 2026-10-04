# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'salary.matrix.mixin']

    salary_reclass_move_id = fields.Many2one(
        'account.move',
        string='Salary Allocation Entry',
        readonly=True,
        copy=False,
        ondelete='set null',
    )

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------
    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        to_allocate = posted.filtered(
            lambda m: m.move_type in ('out_invoice', 'out_refund')
            and m.is_salaries and m.payslip_run_id and not m.salary_reclass_move_id
        )
        for move in to_allocate:
            move._create_salary_allocation_entry()
        return posted

    def button_draft(self):
        self._remove_salary_allocation_entry()
        return super().button_draft()

    def button_cancel(self):
        self._remove_salary_allocation_entry()
        return super().button_cancel()

    # ------------------------------------------------------------------
    # Allocation logic
    # ------------------------------------------------------------------
    def _get_slip_cost(self, slip):
        return slip.employer_cost if 'employer_cost' in slip._fields else slip.net_wage

    def _compute_salary_allocation(self):
        """
        {(rule, rule_account, source_account): amount}  بعملة الشركة، بإشارة موجبة للفاتورة.
        لكل بند موظف في الفاتورة: نسبة = قيمة البند / تكلفة الموظف في الـ payslip،
        وكل رول له حساب بيتضرب قيمته في النسبة دي (فلو عدّلت المبلغ في الويزارد
        التوزيع بيتناسب معاه). اللي مش متوزّع بيفضل في حساب المنتج الأصلي.
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

    @staticmethod
    def _salary_alloc_line(account, balance, name, partner):
        return (0, 0, {
            'account_id': account.id,
            'name': name,
            'partner_id': partner.id,
            'debit': balance if balance > 0 else 0.0,
            'credit': -balance if balance < 0 else 0.0,
        })

    def _create_salary_allocation_entry(self):
        self.ensure_one()
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

        partner = self.partner_id
        line_vals = []
        for (rule, account), amount in credits.items():
            # سطر واحد لكل رول = مجموع الرول من كل الموظفين
            line_vals.append(self._salary_alloc_line(
                account, -currency.round(amount), rule.name, partner))
        for source, amount in debits.items():
            line_vals.append(self._salary_alloc_line(
                source, currency.round(amount),
                _('Salary allocation - %s', self.name), partner))

        journal = self.company_id.salary_reclass_journal_id or self.env['account.journal'].search(
            [('type', '=', 'general'), ('company_id', '=', self.company_id.id)], limit=1)
        if not journal:
            raise UserError(_('No Miscellaneous journal found for salary allocation. '
                              'Set one on the company form.'))

        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'journal_id': journal.id,
            'company_id': self.company_id.id,
            'date': self.date,
            'ref': _('Salary allocation - %s', self.name),
            'line_ids': line_vals,
        })
        entry.action_post()
        self.salary_reclass_move_id = entry
        return entry

    def _remove_salary_allocation_entry(self):
        for move in self.filtered('salary_reclass_move_id'):
            entry = move.salary_reclass_move_id
            move.salary_reclass_move_id = False
            if entry.state == 'posted':
                entry.button_draft()
            entry.unlink()
