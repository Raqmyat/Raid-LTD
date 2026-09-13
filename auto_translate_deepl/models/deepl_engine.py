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

    def translate_text_debug(self, text, source_lang, target_lang):
        """نسخة تشخيصية بترجع تفاصيل كاملة عن أي خطأ - تستخدم من Server
        Action لما مفيش وصول لملفات لوج السيرفر، عشان نشوف السبب الحقيقي
        عن طريق ir.logging (Settings > Technical > Logging) بدل ما
        نستنى نوصل لسيرفر لوج مش متاح.
        """
        api_key = self._get_api_key()
        if not api_key:
            return {'ok': False, 'error': 'NO_API_KEY_SET'}

        url = DEEPL_FREE_URL if api_key.strip().endswith(':fx') else DEEPL_PRO_URL
        masked_key = (api_key[:6] + '...' + api_key[-4:]) if len(api_key) > 12 else '***'

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
            return {
                'ok': response.ok,
                'url': url,
                'masked_key': masked_key,
                'status_code': response.status_code,
                'body': response.text[:500],
            }
        except Exception as e:
            return {
                'ok': False,
                'url': url,
                'masked_key': masked_key,
                'error': '%s: %s' % (type(e).__name__, e),
            }
