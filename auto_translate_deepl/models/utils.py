# -*- coding: utf-8 -*-
import logging
import re

_logger = logging.getLogger(__name__)

# نطاق حروف اللغة العربية (Unicode) - كفاية لتمييز عربي عن إنجليزي في الأسامي
_ARABIC_RE = re.compile(r'[\u0600-\u06FF]')


def is_arabic(text):
    """بيرجع True لو النص فيه ولو حرف عربي واحد."""
    return bool(_ARABIC_RE.search(text or ''))


def auto_translate_field(env, record, field_name):
    """يترجم قيمة حقل translate=True (زي name) من عربي لإنجليزي أو العكس
    باستخدام DeepL، ويخزّن النتيجة في اللغة التانية.

    آمن تمامًا: أي استثناء (مفتاح API غلط، مفيش انترنت، حد الاستخدام
    خلص...) بيتسجل في الـ log وبيتجاهل، ومبيوقفش عملية حفظ السجل الأصلية
    خالص لأنه بيتنفذ بعد الـ super().write/create.
    """
    if env.context.get('skip_auto_translate'):
        return

    value = record[field_name]
    if not value:
        return

    langs = env['res.lang'].sudo().search([('active', '=', True)])
    ar_codes = [lang.code for lang in langs if lang.code.startswith('ar')]
    en_codes = [lang.code for lang in langs if lang.code.startswith('en')]
    if not ar_codes or not en_codes:
        # اللغتين مش مفعّلتين مع بعض في السيستم - مفيش داعي نكمل
        return

    source_is_arabic = is_arabic(value)
    target_codes = en_codes if source_is_arabic else ar_codes
    deepl_source = 'AR' if source_is_arabic else 'EN'
    deepl_target = 'EN-US' if source_is_arabic else 'AR'

    engine = env['deepl.translation.engine']

    for lang_code in target_codes:
        try:
            existing = record.with_context(lang=lang_code)[field_name]
        except Exception:
            existing = False

        # لو فيه قيمة مختلفة عن الأصل محفوظة فعلاً في اللغة دي، معناه
        # فيه ترجمة حقيقية (يدوية أو سابقة) - منلمسهاش عشان منكسرش تعديل
        # المستخدم اليدوي.
        if existing and existing != value:
            continue

        try:
            translated = engine.translate_text(value, deepl_source, deepl_target)
        except Exception:
            _logger.exception(
                'فشل نداء DeepL لترجمة الحقل %s للسجل %s (%s)',
                field_name, record.id, record._name,
            )
            continue

        if not translated:
            continue

        try:
            record.with_context(
                lang=lang_code, skip_auto_translate=True
            ).write({field_name: translated})
        except Exception:
            _logger.exception(
                'فشل حفظ الترجمة التلقائية للحقل %s للسجل %s (%s)',
                field_name, record.id, record._name,
            )
