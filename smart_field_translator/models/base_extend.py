# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

# الموديلات دي بنستثنيها دايمًا عشان منعملش أي حلقة أو نلمس بيانات النظام نفسه
EXCLUDED_MODELS = {
    'translation.rule', 'translation.dictionary', 'translation.engine',
    'ir.model', 'ir.model.fields', 'ir.translation', 'res.lang',
    'ir.module.module',
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
        # منمنعش عملية الـ write الأساسية تفشل بسبب منطق الترجمة، خصوصًا وقت
        # عمليات install/uninstall لأي موديل (بما فيه ir.module.module نفسه)
        # أو لو جدول translation_rule لسه مش موجود لأي سبب.
        if self._name in EXCLUDED_MODELS:
            return res
        try:
            config = self.env['translation.rule']._get_translation_map().get(self._name)
        except Exception:
            _logger.exception(
                'تعذّر قراءة translation_rule أثناء write على %s - تم تجاهل الترجمة التلقائية',
                self._name,
            )
            return res
        if config:
            changed_fields = set(config['fields']) & set(vals.keys())
            if changed_fields:
                self._auto_translate_fields(only_fields=list(changed_fields))
        return res

    # ------------------------------------------------------------------
    def _auto_translate_fields(self, only_fields=None, force=False):
        """يوزّع الترجمة حسب mode القاعدة المهيأة لهذا الموديل."""
        if self._name in EXCLUDED_MODELS or self._transient:
            return
        try:
            config = self.env['translation.rule']._get_translation_map().get(self._name)
        except Exception:
            _logger.exception(
                'تعذّر قراءة translation_rule أثناء _auto_translate_fields على %s',
                self._name,
            )
            return
        if not config:
            return

        target_fields = only_fields or config['fields']
        mode = config['mode']

        if mode == 'transliteration':
            self._auto_translate_side_fields(target_fields, force)
        else:
            self._auto_translate_core_translation(target_fields, force)

    # ------------------------------------------------------------------
    # وضع Transliteration: بيكتب في حقلين جانبيين <field>_ar / <field>_en
    # وبيسيب الحقل الأصلي زي ما هو (آمن 100% ومفيهوش أي تعديل على الداتابيز)
    # ------------------------------------------------------------------
    def _auto_translate_side_fields(self, target_fields, force):
        engine = self.env['translation.engine']
        for record in self:
            for fname in target_fields:
                if fname not in record._fields:
                    continue
                ar_field = f'{fname}_ar'
                en_field = f'{fname}_en'
                if ar_field not in record._fields or en_field not in record._fields:
                    # الحقلين الجانبيين مش متعرّفين على الموديل ده - تجاهل
                    continue

                source_value = record[fname]
                if not source_value:
                    continue

                src_lang = engine.detect_lang(source_value)
                vals = {}

                if src_lang == 'ar':
                    if force or not record[ar_field]:
                        vals[ar_field] = source_value
                    if force or not record[en_field]:
                        translated = engine.transliterate_text(source_value, 'ar', 'en')
                        if translated:
                            vals[en_field] = translated
                else:
                    if force or not record[en_field]:
                        vals[en_field] = source_value
                    if force or not record[ar_field]:
                        translated = engine.transliterate_text(source_value, 'en', 'ar')
                        if translated:
                            vals[ar_field] = translated

                if vals:
                    try:
                        record.with_context(skip_auto_translate=True).write(vals)
                    except Exception:
                        _logger.exception(
                            'فشلت ترجمة (نقحرة) الحقل %s للسجل %s (%s)',
                            fname, record.id, self._name,
                        )

    # ------------------------------------------------------------------
    # وضع Dictionary: بيستخدم نظام الترجمة الأصلي في أودو (translate=True)
    # مناسب بس للحقول اللي أصلاً Translatable زي product.template.name
    # ------------------------------------------------------------------
    def _auto_translate_core_translation(self, target_fields, force):
        langs = self.env['res.lang'].sudo().search([('active', '=', True)])
        ar_codes = [lang.code for lang in langs if lang.code.startswith('ar')]
        en_codes = [lang.code for lang in langs if lang.code.startswith('en')]
        if not ar_codes or not en_codes:
            return

        engine = self.env['translation.engine']

        for record in self:
            for fname in target_fields:
                if fname not in record._fields:
                    continue
                field_def = record._fields[fname]
                if not getattr(field_def, 'translate', False):
                    # الحقل مش Translatable أصلًا - متروجمش فيه بالطريقة دي
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
                        # ملحوظة مهمة: أودو بيرجّع القيمة الأصلية كـ fallback
                        # لو مفيش ترجمة محفوظة فعليًا للغة المطلوبة (بدل ما
                        # يرجع فاضي). فلو القيمة الراجعة مطابقة تمامًا للقيمة
                        # المصدر، ده معناه لسه معندناش ترجمة حقيقية، ولازم
                        # نكمل ونترجم. لو مختلفة فعلاً، يبقى فيه ترجمة حقيقية
                        # موجودة بالفعل ومنلمسهاش.
                        if existing and existing != source_value:
                            continue
                    try:
                        translated = engine.translate_text(source_value, src_code, dst_code)
                    except Exception:
                        _logger.exception(
                            'فشلت ترجمة الحقل %s للسجل %s (%s)', fname, record.id, self._name
                        )
                        continue
                    if not translated:
                        continue
                    try:
                        record.with_context(
                            lang=lang_code, skip_auto_translate=True
                        ).write({fname: translated})
                    except Exception:
                        _logger.exception(
                            'فشلت كتابة ترجمة الحقل %s للسجل %s (%s)',
                            fname, record.id, self._name,
                        )