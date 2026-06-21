# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero


class AccountPaymentAllocationLine(models.Model):
    _name = 'account.payment.allocation.line'
    _description = 'Payment Invoice Allocation Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)

    payment_id = fields.Many2one(
        comodel_name='account.payment',
        string='Payment',
        required=True,
        ondelete='cascade',
        index=True,
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Invoice/Bill',
        required=True,
        ondelete='restrict',
        domain="[('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')), "
               "('state', '=', 'posted'), ('payment_state', 'not in', ('paid', 'reversed'))]",
    )
    partner_id = fields.Many2one(
        related='move_id.partner_id',
        string='Partner',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='payment_id.currency_id',
        string='Currency',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related='payment_id.company_id',
        string='Company',
        store=True,
        readonly=True,
    )

    invoice_date = fields.Date(
        related='move_id.invoice_date',
        string='Invoice Date',
        store=True,
        readonly=True,
    )
    invoice_due_date = fields.Date(
        related='move_id.invoice_date_due',
        string='Due Date',
        store=True,
        readonly=True,
    )
    invoice_total = fields.Monetary(
        string='Invoice Total',
        compute='_compute_invoice_amounts',
        store=True,
        currency_field='currency_id',
    )
    residual_amount = fields.Monetary(
        string='Residual Amount',
        compute='_compute_invoice_amounts',
        store=True,
        currency_field='currency_id',
        help='Outstanding amount on the invoice/bill at the time of computation, '
             'in the payment currency.',
    )

    allocation_method = fields.Selection(
        selection=[
            ('fixed', 'Fixed Amount'),
            ('percentage', 'Percentage'),
        ],
        string='Allocation Method',
        default='fixed',
        required=True,
    )
    allocated_amount = fields.Monetary(
        string='Allocated Amount',
        currency_field='currency_id',
        default=0.0,
    )
    allocated_percentage = fields.Float(
        string='Allocated %',
        default=0.0,
        digits=(16, 2),
    )

    remaining_after_allocation = fields.Monetary(
        string='Remaining After Allocation',
        compute='_compute_remaining_after_allocation',
        store=True,
        currency_field='currency_id',
    )

    allocation_state = fields.Selection(
        selection=[
            ('full', 'Fully Allocated'),
            ('partial', 'Partially Allocated'),
            ('over', 'Over-Allocated'),
            ('none', 'Not Allocated'),
        ],
        string='Allocation Status',
        compute='_compute_allocation_state',
    )

    is_reconciled = fields.Boolean(
        string='Reconciled',
        compute='_compute_is_reconciled',
    )

    # ------------------------------------------------------------
    # Compute methods
    # ------------------------------------------------------------
    @api.depends('move_id.payment_state')
    def _compute_is_reconciled(self):
        for line in self:
            line.is_reconciled = line.move_id.payment_state in ('paid', 'in_payment', 'partial', 'reversed')

    @api.depends('move_id')
    def _compute_invoice_amounts(self):
        for line in self:
            move = line.move_id
            if not move:
                line.invoice_total = 0.0
                line.residual_amount = 0.0
                continue
            # amount_residual is expressed in the invoice currency; convert
            # to the payment currency when they differ.
            if line.currency_id and move.currency_id != line.currency_id:
                line.invoice_total = move.currency_id._convert(
                    move.amount_total, line.currency_id, move.company_id, move.date or fields.Date.today())
                line.residual_amount = move.currency_id._convert(
                    move.amount_residual, line.currency_id, move.company_id, move.date or fields.Date.today())
            else:
                line.invoice_total = move.amount_total
                line.residual_amount = move.amount_residual

    @api.depends('residual_amount', 'allocated_amount')
    def _compute_remaining_after_allocation(self):
        for line in self:
            line.remaining_after_allocation = line.residual_amount - line.allocated_amount

    @api.depends('allocated_amount', 'residual_amount')
    def _compute_allocation_state(self):
        for line in self:
            if line.currency_id and float_is_zero(line.allocated_amount, precision_rounding=line.currency_id.rounding):
                line.allocation_state = 'none'
                continue
            precision = line.currency_id.rounding if line.currency_id else 0.01
            cmp = float_compare(line.allocated_amount, line.residual_amount, precision_rounding=precision)
            if cmp > 0:
                line.allocation_state = 'over'
            elif cmp == 0:
                line.allocation_state = 'full'
            else:
                line.allocation_state = 'partial'

    # ------------------------------------------------------------
    # Onchange: two-way recalculation between amount and percentage
    # ------------------------------------------------------------
    @api.onchange('allocated_percentage')
    def _onchange_allocated_percentage(self):
        for line in self:
            if line.allocation_method != 'percentage':
                continue
            payment_amount = line.payment_id.amount or 0.0
            line.allocated_amount = payment_amount * (line.allocated_percentage or 0.0) / 100.0

    @api.onchange('allocated_amount')
    def _onchange_allocated_amount(self):
        for line in self:
            if line.allocation_method != 'percentage':
                continue
            payment_amount = line.payment_id.amount or 0.0
            if payment_amount:
                line.allocated_percentage = (line.allocated_amount / payment_amount) * 100.0
            else:
                line.allocated_percentage = 0.0

    @api.onchange('allocation_method')
    def _onchange_allocation_method(self):
        for line in self:
            payment_amount = line.payment_id.amount or 0.0
            if line.allocation_method == 'percentage' and payment_amount:
                line.allocated_percentage = (line.allocated_amount / payment_amount) * 100.0
            elif line.allocation_method == 'fixed' and payment_amount:
                line.allocated_amount = payment_amount * (line.allocated_percentage or 0.0) / 100.0

    @api.onchange('move_id')
    def _onchange_move_id(self):
        for line in self:
            if line.move_id:
                line.allocated_amount = min(line.residual_amount, line.payment_id.amount or 0.0)
                if line.payment_id.amount:
                    line.allocated_percentage = (line.allocated_amount / line.payment_id.amount) * 100.0

    # ------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------
    @api.constrains('allocated_amount', 'residual_amount')
    def _check_allocation_not_exceeding_residual(self):
        for line in self:
            if not line.currency_id:
                continue
            precision = line.currency_id.rounding
            if float_compare(line.allocated_amount, line.residual_amount, precision_rounding=precision) > 0:
                raise ValidationError(_(
                    'The allocated amount (%(allocated)s) for invoice %(invoice)s cannot exceed '
                    'its residual amount (%(residual)s).',
                    allocated=line.allocated_amount,
                    invoice=line.move_id.name or line.move_id.display_name,
                    residual=line.residual_amount,
                ))

    @api.constrains('payment_id', 'move_id')
    def _check_invoice_partner_matches_payment(self):
        for line in self:
            if line.payment_id.partner_id and line.move_id.partner_id != line.payment_id.partner_id:
                raise ValidationError(_(
                    'Invoice %(invoice)s belongs to %(invoice_partner)s, which does not match '
                    'the payment partner %(payment_partner)s.',
                    invoice=line.move_id.name or line.move_id.display_name,
                    invoice_partner=line.move_id.partner_id.display_name,
                    payment_partner=line.payment_id.partner_id.display_name,
                ))

    @api.constrains('payment_id', 'move_id')
    def _check_no_duplicate_invoice(self):
        for line in self:
            duplicates = line.payment_id.allocation_line_ids.filtered(
                lambda l: l.move_id == line.move_id and l.id != line.id
            )
            if duplicates:
                raise ValidationError(_(
                    'Invoice %(invoice)s is already allocated on this payment. '
                    'Each invoice can only be selected once.',
                    invoice=line.move_id.name or line.move_id.display_name,
                ))

    # ------------------------------------------------------------
    # Reconciliation
    # ------------------------------------------------------------
    def _get_reconcile_account_move_lines(self):
        """Return (payment_lines, invoice_lines) for this allocation line's
        receivable/payable accounts, restricted to lines not yet fully
        reconciled."""
        self.ensure_one()
        payment_move = self.payment_id.move_id
        invoice_move = self.move_id
        if not payment_move or not invoice_move:
            return self.env['account.move.line'], self.env['account.move.line']

        payment_lines = payment_move.line_ids.filtered(
            lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
            and not l.reconciled
        )
        invoice_lines = invoice_move.line_ids.filtered(
            lambda l: l.account_id in payment_lines.account_id and not l.reconciled
        )
        return payment_lines, invoice_lines

    def action_reconcile(self):
        """Reconcile this single allocation's invoice against the payment.

        Note: when a payment is split across several invoices, use
        account.payment.action_apply_allocations() instead, which builds a
        sequential reconciliation plan so the payment amount is correctly
        distributed across all selected invoices instead of being consumed
        entirely by the first one.
        """
        for line in self:
            if line.is_reconciled:
                continue
            payment_lines, invoice_lines = line._get_reconcile_account_move_lines()
            if not payment_lines or not invoice_lines:
                continue
            (payment_lines + invoice_lines).reconcile()
        return True

    def action_reconcile_and_notify(self):
        self.action_reconcile()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reconciliation Applied'),
                'message': _('The selected allocation(s) have been reconciled against the payment.'),
                'type': 'success',
            },
        }
