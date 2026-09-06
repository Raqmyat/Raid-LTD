# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # حقلين جانبيين بيخزنوا النسختين (الأصل بيفضل زي ما هو في name)
    name_ar = fields.Char(string='الاسم بالعربي', copy=False)
    name_en = fields.Char(string='Name (English)', copy=False)

    @api.depends('name', 'name_ar', 'name_en')
    def _compute_display_name(self):
        super()._compute_display_name()
        lang = self.env.context.get('lang') or self.env.user.lang or ''
        is_arabic_user = lang.startswith('ar')
        for employee in self:
            target_name = employee.name_ar if is_arabic_user else employee.name_en
            if target_name:
                employee.display_name = target_name

    def _read_format(self, fnames, load='_classic_read'):
        """بنعترض القيمة الراجعة لحقل name نفسه (مش بس display_name) عشان
        يظهر مترجم في كل مكان بيقرأ الحقل بالطريقة العادية - فورم، ليست،
        كانبان، تصدير، إلخ."""
        result = super()._read_format(fnames, load=load)
        if 'name' not in fnames:
            return result
        try:
            lang = self.env.context.get('lang') or self.env.user.lang or ''
            is_arabic_user = lang.startswith('ar')
            records_by_id = {rec.id: rec for rec in self}
            for row in result:
                record = records_by_id.get(row.get('id'))
                if not record:
                    continue
                target_name = record.name_ar if is_arabic_user else record.name_en
                if target_name:
                    row['name'] = target_name
        except Exception:
            _logger.exception('فشل استبدال اسم الموظف المترجم أثناء القراءة')
        return result

    def write(self, vals):
        """حماية مهمة: لو الفورم بيرجّع نفس القيمة المترجمة المعروضة (من
        _read_format فوق) من غير ما اليوزر يقصد يغيّر الاسم فعليًا، لازم
        منسمحش للقيمة المترجمة دي إنها تكتب فوق الاسم الأصلي في name.
        بنسمح بالكتابة بس لو القيمة الجديدة فعلاً مختلفة عن أي نسخة معروفة."""
        if 'name' in vals:
            incoming = vals['name']
            skip_records = self.browse()
            keep_records = self.browse()
            for employee in self:
                if (
                    incoming
                    and incoming != employee.name
                    and incoming in (employee.name_ar, employee.name_en)
                ):
                    skip_records |= employee
                else:
                    keep_records |= employee

            res = True
            if skip_records:
                vals_without_name = {k: v for k, v in vals.items() if k != 'name'}
                if vals_without_name:
                    res = super(HrEmployee, skip_records).write(vals_without_name)
            if keep_records:
                res = super(HrEmployee, keep_records).write(vals)
        else:
            res = super().write(vals)

        if {'name_ar', 'name_en'} & set(vals.keys()):
            self.invalidate_recordset(['display_name'])
        return res
