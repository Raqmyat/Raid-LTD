# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # الحقل الأصلي في hr.employee مش Translatable (translate=False)،
    # فبنعيد تعريفه هنا كـ translate=True عشان يقدر يخزن نسخة عربي
    # ونسخة إنجليزي منفصلتين لنفس السجل، بدل ما القيمة تتكتب فوق بعضها.
    name = fields.Char(translate=True)
