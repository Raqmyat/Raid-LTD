# -*- coding: utf-8 -*-
import logging

import requests

from odoo import models

_logger = logging.getLogger(__name__)

DEEPL_FREE_URL = 'https://api-free.deepl.com/v2/translate'
DEEPL_PRO_URL = 'https://api.deepl.com/v2/translate'


class DeeplTranslationEngine(models.AbstractModel):
    """غلاف بسيط لاستدعاء DeepL API. مفيش أي حالة محفوظة (state) - بس
    دالة ترجمة واحدة بتستخدم مفتاح API من System Parameters.
    """
    _name = 'deepl.translation.engine'
    _description = 'DeepL Translation Engine (Free/Pro)'

    def _get_api_key(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'auto_translate_deepl.api_key'
        )

    def translate_text(self, text, source_lang, target_lang):
        """بيترجم text من source_lang إلى target_lang (أكواد DeepL زي
        'AR', 'EN-US'). بيرجع النص المترجم أو False لو فشل أو مفيش
        مفتاح API متسجل.
        """
        api_key = self._get_api_key()
        if not api_key:
            _logger.warning(
                'مفتاح DeepL API مش متسجّل (System Parameters -> '
                'auto_translate_deepl.api_key) - تم تجاهل الترجمة'
            )
            return False

        # المفاتيح المجانية بتنتهي بـ ":fx" وبتستخدم endpoint مختلف عن المدفوع
        url = DEEPL_FREE_URL if api_key.strip().endswith(':fx') else DEEPL_PRO_URL

        try:
            response = requests.post(
                url,
                data={
                    'auth_key': api_key,
                    'text': text,
                    'source_lang': source_lang,
                    'target_lang': target_lang,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            translations = data.get('translations') or []
            if translations:
                return translations[0].get('text') or False
        except Exception:
            _logger.exception('فشل الاتصال بـ DeepL API')
        return False
