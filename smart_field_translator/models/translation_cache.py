# -*- coding: utf-8 -*-
from odoo import api, fields, models


class TranslationCache(models.Model):
    _name = 'translation.cache'
    _description = 'كاش ترجمات Google Translate (لتقليل عدد الطلبات المرسلة)'
    _rec_name = 'source_text'

    source_text = fields.Char(string='النص الأصلي', required=True)
    source_lang = fields.Char(string='من لغة', required=True)
    target_lang = fields.Char(string='إلى لغة', required=True)
    translated_text = fields.Char(string='الترجمة')

    _sql_constraints = [
        ('cache_uniq', 'unique(source_text, source_lang, target_lang)',
         'يوجد بالفعل ترجمة مخزنة لنفس النص ونفس اللغتين!'),
    ]

    @api.model
    def _get_cached(self, text, source_lang, target_lang):
        """يرجع القيمة المخزنة (ممكن تكون '' لو جوجل فشل قبل كده)، أو None
        لو النص ده معندناش عنه أي كاش خالص لسه."""
        record = self.sudo().search([
            ('source_text', '=', text),
            ('source_lang', '=', source_lang),
            ('target_lang', '=', target_lang),
        ], limit=1)
        if not record:
            return None
        return record.translated_text

    @api.model
    def _set_cached(self, text, source_lang, target_lang, translated_text):
        existing = self.sudo().search([
            ('source_text', '=', text),
            ('source_lang', '=', source_lang),
            ('target_lang', '=', target_lang),
        ], limit=1)
        if existing:
            existing.translated_text = translated_text
        else:
            self.sudo().create({
                'source_text': text,
                'source_lang': source_lang,
                'target_lang': target_lang,
                'translated_text': translated_text,
            })

    def action_clear_cache(self):
        """للأدمن: يمسح كل الكاش المخزّن (لو عايز يجبر الموديول يترجم من
        جوجل تاني بدل ما يستخدم نتيجة قديمة، مثلًا بعد ما وسّع القاموس)."""
        self.search([]).unlink()
