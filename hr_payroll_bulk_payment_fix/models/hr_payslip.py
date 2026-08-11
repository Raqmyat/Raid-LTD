# -*- coding: utf-8 -*-
from odoo import models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def message_post(self, **kwargs):
        """
        hr_payroll_account بينادي payslip.message_post(...) لما تسجل دفع،
        وأحيانًا الـ payslip ده بيكون فعليًا أكتر من سجل (لو كذا payslip
        مرتبطين بنفس القيد المحاسبي - زي لما يكون خيار "Batch Account
        Move Lines" مفعّل). message_post الأصلي محتاج سجل واحد بس
        (self.ensure_one()) وبيرمي:
            ValueError: Expected singleton: hr.payslip(...)

        هنا بنلف على كل سجل لوحده ونعمل post عليه منفصل بدل ما نرمي Error.
        """
        if len(self) > 1:
            for record in self:
                super(HrPayslip, record).message_post(**kwargs)
            return True
        return super().message_post(**kwargs)
