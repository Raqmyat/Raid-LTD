# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .utils import auto_translate_field


class ResCompany(models.Model):
    """اسم الشركة (res.company.name) مرتبط بحقل partner_id.name، وده بيخلي
    نوعه لازم يتطابق مع res.partner.name (translate=True). التعريف الصريح
    هنا بيجبر أودو يعيد حساب الـ schema بتاع عمود name في جدول res_company
    نفسه (تحويله من varchar عادي إلى jsonb) بدل ما يفضل غير متزامن مع
    partner ويسبب تعارض في نوع العمود.
    """
    _inherit = 'res.company'

    name = fields.Char(translate=True)

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals and not self.env.context.get('skip_auto_translate'):
            for record in self:
                auto_translate_field(self.env, record, 'name')
        return res
