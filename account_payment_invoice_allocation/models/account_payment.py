# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # الحقول والـ Computes الأساسية للموديول (تبق كما هي)
    allocation_type = fields.Selection(
        selection=[
            ('invoice', 'Invoice Payment'),
            ('advance', 'Advance Payment'),
        ],
        string='Allocation Type',
        default='invoice',
        required=True,
        tracking=True,
    )
    allocation_line_ids = fields.One2many(
        comodel_name='account.payment.allocation.line',
        inverse_name='payment_id',
        string='Invoice Allocations',
        copy=False,
    )
    allocation_count = fields.Integer(
        string='Allocation Count',
        compute='_compute_allocation_count',
    )
    total_allocated_amount = fields.Monetary(
        string='Total Allocated',
        compute='_compute_allocation_totals',
        currency_field='currency_id',
    )
    remaining_unallocated_amount = fields.Monetary(
        string='Remaining Unallocated',
        compute='_compute_allocation_totals',
        currency_field='currency_id',
    )
    allocation_status = fields.Selection(
        selection=[
            ('full', 'Fully Allocated'),
            ('partial', 'Partially Allocated'),
            ('over', 'Over Allocated'),
        ],
        string='Allocation Status',
        compute='_compute_allocation_totals',
    )

    @api.depends('allocation_line_ids')
    def _compute_allocation_count(self):
        for payment in self:
            payment.allocation_count = len(payment.allocation_line_ids.mapped('move_id'))

    @api.depends('allocation_line_ids', 'amount', 'currency_id')
    def _compute_allocation_totals(self):
        for payment in self:
            total_allocated = sum(payment.allocation_line_ids.mapped('allocated_amount'))
            payment.total_allocated_amount = total_allocated
            payment.remaining_unallocated_amount = payment.amount - total_allocated
            
            if float_is_zero(payment.amount, precision_rounding=payment.currency_id.rounding):
                payment.allocation_status = 'full'
            else:
                compare_res = float_compare(total_allocated, payment.amount, precision_rounding=payment.currency_id.rounding)
                if compare_res == 0:
                    payment.allocation_status = 'full'
                elif compare_res < 0:
                    payment.allocation_status = 'partial'
                else:
                    payment.allocation_status = 'over'

    def action_view_allocated_invoices(self):
        self.ensure_one()
        invoice_ids = self.allocation_line_ids.mapped('move_id').ids
        action = {
            'name': _('Allocated Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(invoice_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': invoice_ids[0],
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', invoice_ids)],
            })
        return action

    # ==========================================================
    # إصلاح التوقيع البرمجي (Signature) لمنع خطأ الـ TypeError
    # وضمان تفكيك الأسطر وحمايتها من الـ Auto-Grouping
    # ==========================================================
    def _prepare_move_line_default_vals(self, write_off_line_vals=None, **kwargs):
        """
        باستخدام **kwargs نضمن استقبال force_balance أو أي حجة أخرى يطلبها أودو بشكل ديناميكي.
        """
        # تمرير جميع المعاملات للدالة الأساسية بأمان
        res = super(AccountPayment, self)._prepare_move_line_default_vals(write_off_line_vals=write_off_line_vals, **kwargs)
        
        if self.allocation_type != 'invoice' or not self.allocation_line_ids:
            return res

        partner_account_id = self.destination_account_id.id
        partner_line = next((line for line in res if line.get('account_id') == partner_account_id), None)
        
        if not partner_line:
            return res

        # حذف السطر المجمع الافتراضي واستبداله بأسطر منفصلة فريدة
        res.remove(partner_line)
        
        is_debit = partner_line.get('debit', 0.0) > 0.0
        total_amount = self.amount
        allocated_total = 0.0

        for alloc_line in self.allocation_line_ids:
            if float_is_zero(alloc_line.allocated_amount, precision_rounding=self.currency_id.rounding):
                continue
                
            amount_to_line = alloc_line.allocated_amount
            allocated_total += amount_to_line
            ratio = amount_to_line / total_amount if total_amount else 0.0
            
            new_line = partner_line.copy()
            # هنا نضع اسم الفاتورة في البيان لضمان النزول بأسطر متعددة بلا دمج
            new_line.update({
                'name': f"Allocation for {alloc_line.move_id.name}",
                'debit': partner_line.get('debit', 0.0) * ratio if is_debit else 0.0,
                'credit': partner_line.get('credit', 0.0) * ratio if not is_debit else 0.0,
                'amount_currency': partner_line.get('amount_currency', 0.0) * ratio,
            })
            res.append(new_line)

        # المتبقي غير الموزع
        remaining_amount = total_amount - allocated_total
        if float_compare(remaining_amount, 0.0, precision_rounding=self.currency_id.rounding) > 0:
            ratio = remaining_amount / total_amount
            advance_line = partner_line.copy()
            advance_line.update({
                'name': "Unallocated Advance Balance",
                'debit': partner_line.get('debit', 0.0) * ratio if is_debit else 0.0,
                'credit': partner_line.get('credit', 0.0) * ratio if not is_debit else 0.0,
                'amount_currency': partner_line.get('amount_currency', 0.0) * ratio,
            })
            res.append(advance_line)

        return res

    # ==========================================================
    # دالة التسوية الذكية المعتمدة على الـ Matching الدقيق للمبالغ والبيان
    # ==========================================================
    def action_apply_allocations(self):
        self.ensure_one()
        if self.state not in ('in_process', 'paid', 'posted', 'done'):
            return

        lines_to_reconcile = self.allocation_line_ids.filtered(lambda l: not l.is_reconciled)
        if not lines_to_reconcile:
            raise ValidationError(_('No pending allocations to apply.'))

        payment_lines = self.move_id.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable') and not l.reconciled
        )
        if not payment_lines:
            raise ValidationError(_('No receivable/payable line was found on this payment to reconcile.'))

        plan = []
        applied_moves = self.env['account.move']
        
        for alloc_line in lines_to_reconcile:
            invoice_lines = alloc_line.move_id.line_ids.filtered(
                lambda l: l.account_id in payment_lines.account_id and not l.reconciled
            )
            if not invoice_lines:
                continue
            
            # مطابقة السطر المحاسبي ذو البيان الفريد مع الفاتورة المقصودة مباشرة
            specific_payment_line = payment_lines.filtered(
                lambda p: p.name == f"Allocation for {alloc_line.move_id.name}" and p.account_id == invoice_lines[0].account_id
            )
            
            if not specific_payment_line:
                specific_payment_line = payment_lines.filtered(
                    lambda p: not p.reconciled and p.account_id == invoice_lines[0].account_id
                )
                if specific_payment_line:
                    specific_payment_line = specific_payment_line[0]

            if specific_payment_line:
                plan.append(specific_payment_line + invoice_lines)
                applied_moves |= alloc_line.move_id

        if not plan:
            raise ValidationError(_('None of the selected allocations could be reconciled.'))

        self.env['account.move.line']._reconcile_plan(plan)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Allocations Applied'),
                'message': _('%(count)s invoice(s) reconciled against payment %(name)s.', count=len(applied_moves), name=self.name),
                'type': 'success',
                'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
            },
        }