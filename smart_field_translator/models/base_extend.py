# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# الموديلات دي بنستثنيها دايمًا عشان منعملش أي حلقة أو نلمس بيانات النظام نفسه
EXCLUDED_MODELS = {
    'translation.rule', 'translation.dictionary', 'translation.engine',
    'ir.model', 'ir.model.fields', 'ir.translation', 'res.lang',
}


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_auto_translate'):
            records._auto_translate_fields()
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('skip_auto_translate'):
            return res
        config = self.env['translation.rule']._get_translation_map().get(self._name)
        if config:
            changed_fields = set(config['fields']) & set(vals.keys())
            if changed_fields:
                self._auto_translate_fields(only_fields=list(changed_fields))
        return res

    # ------------------------------------------------------------------
    def _auto_translate_fields(self, only_fields=None, force=False):
        """يترجم تلقائيًا الحقول المهيأة لهذا الموديل لكل السجلات في self."""
        if self._name in EXCLUDED_MODELS or self._transient:
            return
        config = self.env['translation.rule']._get_translation_map().get(self._name)
        if not config:
            return

        target_fields = only_fields or config['fields']
        mode = config['mode']

        langs = self.env['res.lang'].sudo().search([('active', '=', True)])
        ar_codes = [lang.code for lang in langs if lang.code.startswith('ar')]
        en_codes = [lang.code for lang in langs if lang.code.startswith('en')]
        if not ar_codes or not en_codes:
            # لازم اللغتين مفعّلتين في Settings > Translations عشان الميكانيزم يشتغل
            return

        engine = self.env['translation.engine']
        translator_func = (
            engine.transliterate_text if mode == 'transliteration' else engine.translate_text
        )

        for record in self:
            for fname in target_fields:
                if fname not in record._fields:
                    continue
                source_value = record[fname]
                if not source_value:
                    continue
                src_lang = engine.detect_lang(source_value)
                target_codes = en_codes if src_lang == 'ar' else ar_codes
                src_code = 'ar' if src_lang == 'ar' else 'en'
                dst_code = 'en' if src_lang == 'ar' else 'ar'

                for lang_code in target_codes:
                    if not force:
                        existing = record.with_context(lang=lang_code)[fname]
                        if existing:
                            continue
                    try:
                        translated = translator_func(source_value, src_code, dst_code)
                    except Exception:
                        _logger.exception(
                            'فشلت ترجمة الحقل %s للسجل %s (%s)', fname, record.id, self._name
                        )
                        continue
                    if not translated:
                        continue
                    record.with_context(
                        lang=lang_code, skip_auto_translate=True
                    ).write({fname: translated})
