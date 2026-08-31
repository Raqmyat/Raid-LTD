# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class TranslationDictionary(models.Model):
    _name = 'translation.dictionary'
    _description = 'قاموس الترجمة التلقائية (عربي / إنجليزي)'
    _rec_name = 'word_en'

    word_en = fields.Char(
        string='English Word / Phrase', required=True, index=True,
        help='ممكن تكون كلمة واحدة أو جملة كاملة (مثلاً اسم موظف أو منتج بالكامل).',
    )
    word_ar = fields.Char(
        string='الكلمة أو الجملة بالعربي', required=True, index=True,
    )
    is_proper_name = fields.Boolean(
        string='اسم علم (Proper Name)',
        help='فعّل هذا الخيار لو الكلمة اسم شخص، للتوثيق فقط - مش بيأثر على '
             'آلية الترجمة نفسها.',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('word_en_uniq', 'unique(word_en)', 'هذه الكلمة الإنجليزية موجودة بالفعل في القاموس!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    @api.model
    @tools.ormcache()
    def _get_dictionary_maps(self):
        """يرجع (en_to_ar, ar_to_en) كـ dict للكلمات المفعّلة فقط."""
        entries = self.sudo().search_read(
            [('active', '=', True)], ['word_en', 'word_ar']
        )
        en_to_ar = {}
        ar_to_en = {}
        for entry in entries:
            if entry['word_en']:
                en_to_ar[entry['word_en'].strip().lower()] = entry['word_ar'].strip()
            if entry['word_ar']:
                ar_to_en[entry['word_ar'].strip()] = entry['word_en'].strip()
        return en_to_ar, ar_to_en
