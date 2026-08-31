# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # بدل ما نغيّر translate على الحقل الأصلي name (خطوة خطيرة بتغيّر نوع
    # العمود في الداتابيز وممكن تكسر حاجات تانية في السيستم)، بنستخدم
    # حقلين جانبيين عاديين تمامًا، والاسم الأصلي name يفضل زي ما هو
    # من غير أي تعديل على تعريفه أو نوعه.
    name_ar = fields.Char(string='الاسم بالعربي', copy=False)
    name_en = fields.Char(string='Name (English)', copy=False)

    @api.depends('name', 'name_ar', 'name_en')
    def _compute_display_name(self):
        super()._compute_display_name()
        lang = self.env.user.lang or ''
        is_arabic_user = lang.startswith('ar')
        for employee in self:
            target_name = employee.name_ar if is_arabic_user else employee.name_en
            if target_name:
                employee.display_name = target_name

    def write(self, vals):
        res = super().write(vals)
        if {'name_ar', 'name_en'} & set(vals.keys()):
            # نجبر display_name يتحسب من جديد فورًا بدل ما يفضل القيمة
            # القديمة كاش لحد ما يحصل ريكوست جديد
            self.invalidate_recordset(['display_name'])
        return res
