# -*- coding: utf-8 -*-
import logging
import re

import requests

from odoo import api, models

_logger = logging.getLogger(__name__)

ARABIC_RANGE = re.compile(r'[\u0600-\u06FF]')

GOOGLE_TRANSLATE_URL = 'https://translate.googleapis.com/translate_a/single'
REQUEST_TIMEOUT = 6

# خريطة تحويل الحروف العربية إلى لاتينية (Transliteration) - تستخدم فقط
# كـ fallback محلي لو تعذّر الاتصال بجوجل (مفيش إنترنت / السيرفر واقع مؤقتًا)
AR_TO_LATIN = {
    'ا': 'a', 'أ': 'a', 'إ': 'i', 'آ': 'aa', 'ب': 'b', 'ت': 't', 'ث': 'th',
    'ج': 'j', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'th', 'ر': 'r', 'ز': 'z',
    'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'd', 'ط': 't', 'ظ': 'z', 'ع': 'a',
    'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n',
    'ه': 'h', 'و': 'w', 'ي': 'y', 'ى': 'a', 'ة': 'a', 'ء': '', 'ئ': 'e',
    'ؤ': 'o', 'لا': 'la',
    '\u064B': '', '\u064C': '', '\u064D': '', '\u064E': '', '\u064F': '',
    '\u0650': '', '\u0651': '', '\u0652': '',
}

PUNCT_RE = re.compile(r'^([\W_]*)(.*?)([\W_]*)$', re.UNICODE)


class TranslationEngine(models.AbstractModel):
    _name = 'translation.engine'
    _description = 'محرك الترجمة (Google Translate مجاني + قاموس استثناءات)'

    # ------------------------------------------------------------------
    # أدوات مساعدة عامة
    # ------------------------------------------------------------------
    @api.model
    def detect_lang(self, text):
        """يحدد إذا كان النص عربي أو إنجليزي بناءً على وجود حروف عربية."""
        if not text:
            return False
        return 'ar' if ARABIC_RANGE.search(text) else 'en'

    @api.model
    def _split_token(self, token):
        match = PUNCT_RE.match(token)
        if match:
            return match.group(1), match.group(2), match.group(3)
        return '', token, ''

    # ------------------------------------------------------------------
    # طبقة الاستثناءات: القاموس اليدوي (الأدمن هو اللي بيتحكم فيها)
    # لو النص (كامل - مش كلمة كلمة) موجود في القاموس، بناخد قيمته على طول
    # من غير ما نكلم جوجل أصلاً. ده بيدي الأدمن سيطرة كاملة على أي حالة
    # عايز يفرض ترجمة معينة ليها (اسم شركة، مصطلح داخلي، غلطة جوجل...).
    # ------------------------------------------------------------------
    @api.model
    def _dictionary_override(self, text, source_lang):
        if not text:
            return None
        en_to_ar, ar_to_en = self.env['translation.dictionary']._get_dictionary_maps()
        stripped = text.strip()
        if source_lang == 'ar':
            return ar_to_en.get(stripped)
        return en_to_ar.get(stripped.lower())

    # ------------------------------------------------------------------
    # Google Translate (النسخة المجانية غير الرسمية - بدون API Key)
    # مع كاش دائم في translation.cache عشان:
    #   1) نقلل عدد الطلبات المرسلة لجوجل (أداء + تقليل احتمال الحظر المؤقت)
    #   2) نفس النص ميتترجمش تاني كل مرة، حتى بعد ريستارت السيرفر
    # ------------------------------------------------------------------
    @api.model
    def _google_translate(self, text, source_lang, target_lang):
        if not text or not text.strip():
            return None

        Cache = self.env['translation.cache']
        cached = Cache._get_cached(text, source_lang, target_lang)
        if cached is not None:
            return cached or None

        translated = self._google_translate_http(text, source_lang, target_lang)
        # بنخزن في الكاش حتى لو النتيجة None (يعني جوجل فشل/رجع فاضي) بقيمة
        # فاضية عشان مانضربش نفس الطلب كل شوية
        Cache._set_cached(text, source_lang, target_lang, translated or '')
        return translated

    @api.model
    def _google_translate_http(self, text, source_lang, target_lang):
        try:
            response = requests.get(
                GOOGLE_TRANSLATE_URL,
                params={
                    'client': 'gtx',
                    'sl': source_lang,
                    'tl': target_lang,
                    'dt': 't',
                    'q': text,
                },
                timeout=REQUEST_TIMEOUT,
                headers={'User-Agent': 'Mozilla/5.0'},
            )
            response.raise_for_status()
            data = response.json()
            translated = ''.join(chunk[0] for chunk in data[0] if chunk and chunk[0])
            translated = translated.strip()
            if not translated or translated.strip().lower() == text.strip().lower():
                # جوجل رجّع نفس النص أو مفيش حاجة - يعني مش لاقي ترجمة حقيقية
                return None
            return translated
        except Exception:
            _logger.warning(
                'فشل الاتصال بـ Google Translate (sl=%s, tl=%s) للنص: %s',
                source_lang, target_lang, text, exc_info=True,
            )
            return None

    # ------------------------------------------------------------------
    # وضع الترجمة العامة (Dictionary mode) - للمنتجات والفئات وما شابه
    # ------------------------------------------------------------------
    @api.model
    def translate_text(self, text, source_lang, target_lang):
        if not text:
            return None
        override = self._dictionary_override(text, source_lang)
        if override:
            return override
        return self._google_translate(text, source_lang, target_lang)

    # ------------------------------------------------------------------
    # وضع النقحرة (Transliteration mode) - لأسماء الأشخاص
    #
    # الأسماء بطبيعتها بتتكوّن من أجزاء مستقلة (اسم أول + تاني + عائلة)،
    # فبدل ما نحاول نلاقي "الجملة كاملة" في القاموس (شبه مستحيل)، بنفكك
    # الاسم لأجزاء ونجرب كل جزء لوحده، مع محاولة مركّبات من كلمتين الأول
    # (زي "عبد الرحمن") قبل ما نرجع لكلمة واحدة.
    # ------------------------------------------------------------------
    @api.model
    def transliterate_text(self, text, source_lang, target_lang):
        if not text:
            return None

        full_override = self._dictionary_override(text, source_lang)
        if full_override:
            return full_override

        words = [w for w in text.strip().split(' ') if w]
        if not words:
            return None

        en_to_ar, ar_to_en = self.env['translation.dictionary']._get_dictionary_maps()
        dictionary_map = ar_to_en if source_lang == 'ar' else en_to_ar

        result_parts = []
        i = 0
        while i < len(words):
            matched = False
            # جرب مركّب من كلمتين الأول (زي "عبد الرحمن")
            if i + 1 < len(words):
                two_word_key = f'{words[i]} {words[i + 1]}'
                lookup_key = two_word_key if source_lang == 'ar' else two_word_key.lower()
                hit = dictionary_map.get(lookup_key)
                if hit:
                    result_parts.append(hit)
                    i += 2
                    matched = True
            if matched:
                continue

            # جرب الكلمة لوحدها
            one_word = words[i]
            lookup_key = one_word if source_lang == 'ar' else one_word.lower()
            hit = dictionary_map.get(lookup_key)
            if hit:
                result_parts.append(hit)
            else:
                # مفيش حاجة في القاموس - جرب جوجل، ولو فشل ارجع للنقحرة المحلية
                fallback = self._google_translate(one_word, source_lang, target_lang)
                if not fallback and source_lang == 'ar' and target_lang == 'en':
                    fallback = self._local_transliterate_ar_to_en(one_word)
                result_parts.append(fallback or one_word)
            i += 1

        if not result_parts:
            return None
        return ' '.join(result_parts).strip()

    @api.model
    def _local_transliterate_ar_to_en(self, text):
        words = text.split(' ')
        result_words = []
        for word in words:
            prefix, core, suffix = self._split_token(word)
            if not core:
                result_words.append(word)
                continue
            result_words.append(f'{prefix}{self._transliterate_arabic_word(core)}{suffix}')
        result = ' '.join(w for w in result_words if w).strip().title()
        return result or None

    @api.model
    def _transliterate_arabic_word(self, word):
        result = []
        i = 0
        length = len(word)
        while i < length:
            two_char = word[i:i + 2]
            if two_char in AR_TO_LATIN:
                result.append(AR_TO_LATIN[two_char])
                i += 2
                continue
            char = word[i]
            result.append(AR_TO_LATIN.get(char, char))
            i += 1
        latin = ''.join(result)
        latin = re.sub(r'(.)\1{2,}', r'\1\1', latin)
        return latin
