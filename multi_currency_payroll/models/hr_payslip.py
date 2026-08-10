# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
        readonly=False,
        help='بتتحدد تلقائي من عملة الـ version (العقد سابقًا)، وتقدر تعدلها يدويًا لو لزم.',
    )

    def _get_version(self):
        """
        رجّع الـ hr.version المرتبط بالـ payslip.
        بما إن hr.contract اتلغى وبقى hr.version في v19، الحقل اللي بيربط
        الـ payslip بالنسخة ممكن يكون لسه اسمه `contract_id` (مع تغيير الموديل
        اللي بيشاور عليه من جوه) أو ممكن يبقى اتسمى `version_id`.
        هنا بنتأكد أوتوماتيك من الاسم الموجود عندك فعليًا.
        """
        self.ensure_one()
        if 'version_id' in self._fields:
            return self.version_id
        if 'contract_id' in self._fields:
            return self.contract_id
        return self.env['hr.version']

    @api.depends('company_id')
    def _compute_currency_id(self):
        for slip in self:
            version = slip._get_version()
            slip.currency_id = (
                version.currency_id
                if version and version.currency_id
                else slip.company_id.currency_id
            )

    def action_payslip_done(self):
        """
        بعد ما أودو يعمل الحساب والتأكيد وينشئ القيد المحاسبي بالشكل العادي
        (بعملة الشركة)، بنصحح القيد ده عشان يعكس عملة الـ payslip الحقيقية
        (amount_currency) مع تحويل صحيح لعملة الشركة بسعر الصرف في تاريخ الصرف.

        ملحوظة: بنفترض إن فيه حقل `move_id` على hr.payslip بيشاور على قيد
        account.move الناتج. لو الاسم مختلف عندك، غيّر `self.move_id` هنا.
        """
        res = super().action_payslip_done()

        for slip in self:
            move = getattr(slip, 'move_id', False)
            if not move or not slip.currency_id:
                continue
            if slip.currency_id == slip.company_id.currency_id:
                continue
            if move.state != 'draft':
                continue

            move.currency_id = slip.currency_id
            date = move.date or fields.Date.context_today(slip)

            for line in move.line_ids:
                original_amount = line.debit - line.credit
                company_currency = move.company_id.currency_id
                converted_amount = slip.currency_id._convert(
                    original_amount,
                    company_currency,
                    move.company_id,
                    date,
                )
                line.write({
                    'currency_id': slip.currency_id.id,
                    'amount_currency': original_amount,
                    'debit': converted_amount if converted_amount > 0 else 0.0,
                    'credit': -converted_amount if converted_amount < 0 else 0.0,
                })

        return res
