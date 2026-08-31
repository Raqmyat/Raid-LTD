# -*- coding: utf-8 -*-
import re

from odoo import api, models

ARABIC_RANGE = re.compile(r'[\u0600-\u06FF]')

# خريطة تحويل الحروف العربية إلى لاتينية (Transliteration) - تقريبية
AR_TO_LATIN = {
    'ا': 'a', 'أ': 'a', 'إ': 'i', 'آ': 'aa', 'ب': 'b', 'ت': 't', 'ث': 'th',
    'ج': 'j', 'ح': 'h', 'خ': 'kh', 'د': 'd', 'ذ': 'th', 'ر': 'r', 'ز': 'z',
    'س': 's', 'ش': 'sh', 'ص': 's', 'ض': 'd', 'ط': 't', 'ظ': 'z', 'ع': 'a',
    'غ': 'gh', 'ف': 'f', 'ق': 'q', 'ك': 'k', 'ل': 'l', 'م': 'm', 'ن': 'n',
    'ه': 'h', 'و': 'w', 'ي': 'y', 'ى': 'a', 'ة': 'a', 'ء': '', 'ئ': 'e',
    'ؤ': 'o', 'لا': 'la',
    # تشكيل - يُتجاهل
    '\u064B': '', '\u064C': '', '\u064D': '', '\u064E': '', '\u064F': '',
    '\u0650': '', '\u0651': '', '\u0652': '',
}

# كلمات بادئة شائعة قبل الأسماء يتم حذفها من الـ transliteration الحرفي
# (الدمج يتم عبر القاموس لو المستخدم ضاف كلمة is_proper_name)

PUNCT_RE = re.compile(r'^([\W_]*)(.*?)([\W_]*)$', re.UNICODE)


class TranslationEngine(models.AbstractModel):
    _name = 'translation.engine'
    _description = 'محرك الترجمة المحلي المجاني'

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
        """يفصل علامات الترقيم الملتصقة بالكلمة عن الكلمة نفسها."""
        match = PUNCT_RE.match(token)
        if match:
            return match.group(1), match.group(2), match.group(3)
        return '', token, ''

    # ------------------------------------------------------------------
    # وضع الترجمة العامة (Dictionary) - للمنتجات والفئات وما شابه
    # ------------------------------------------------------------------
    @api.model
    def translate_text(self, text, source_lang, target_lang):
        """ترجمة كلمة بكلمة بالاعتماد على القاموس. يرجع None لو محدش الكلمات
        الأساسية موجودة في القاموس (يعني مفيش فايدة نكتب نص مطابق للأصل)."""
        if not text:
            return None
        en_to_ar, ar_to_en = self.env['translation.dictionary']._get_dictionary_maps()
        tokens = text.split(' ')
        translated_tokens = []
        found_any = False
        for token in tokens:
            prefix, word, suffix = self._split_token(token)
            if not word:
                translated_tokens.append(token)
                continue
            if source_lang == 'ar':
                translated_word = ar_to_en.get(word)
            else:
                translated_word = en_to_ar.get(word.lower())
            if translated_word:
                found_any = True
                translated_tokens.append(f'{prefix}{translated_word}{suffix}')
            else:
                # ما لقيناش ترجمة للكلمة دي - نسيبها زي ما هي
                translated_tokens.append(token)
        if not found_any:
            return None
        return ' '.join(translated_tokens)

    # ------------------------------------------------------------------
    # وضع النقحرة (Transliteration) - لأسماء الأشخاص
    # ------------------------------------------------------------------
    @api.model
    def transliterate_text(self, text, source_lang, target_lang):
        if not text:
            return None
        en_to_ar, ar_to_en = self.env['translation.dictionary']._get_dictionary_maps()

        if source_lang == 'ar' and target_lang == 'en':
            words = text.split(' ')
            result_words = []
            for word in words:
                prefix, core, suffix = self._split_token(word)
                if not core:
                    result_words.append(word)
                    continue
                # لو الاسم موجود جاهز في القاموس بالنقحرة الصحيحة، استخدمه
                dict_hit = ar_to_en.get(core)
                if dict_hit:
                    result_words.append(f'{prefix}{dict_hit}{suffix}')
                    continue
                result_words.append(f'{prefix}{self._transliterate_arabic_word(core)}{suffix}')
            return ' '.join(w for w in result_words if w).strip().title()

        if source_lang == 'en' and target_lang == 'ar':
            # النقحرة العكسية (إنجليزي -> عربي) غير موثوقة بخوارزمية بسيطة،
            # فبنعتمد فقط على القاموس (أسماء جاهزة أضافها الأدمن)
            words = text.split(' ')
            result_words = []
            found_any = False
            for word in words:
                prefix, core, suffix = self._split_token(word)
                if not core:
                    result_words.append(word)
                    continue
                dict_hit = en_to_ar.get(core.lower())
                if dict_hit:
                    found_any = True
                    result_words.append(f'{prefix}{dict_hit}{suffix}')
                else:
                    result_words.append(word)
            if not found_any:
                return None
            return ' '.join(result_words)

        return None

    @api.model
    def _transliterate_arabic_word(self, word):
        # معالجة خاصة لـ "ال" التعريف
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
        # تنظيف تكرار الحروف الناتج عن الدمج
        latin = re.sub(r'(.)\1{2,}', r'\1\1', latin)
        return latin
