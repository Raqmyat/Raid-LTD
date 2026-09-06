# -*- coding: utf-8 -*-
{
    'name': 'Smart Field Auto Translator',
    'version': '19.0.2.0.0',
    'summary': 'ترجمة تلقائية لأي حقل نصي (موظفين، منتجات، ...) حسب لغة النظام - بمحرك Google Translate المجاني',
    'description': """
Smart Field Auto Translator
============================
يسمح للأدمن بتحديد أي موديل وأي حقل ليتم ترجمته تلقائيًا فور الإنشاء أو
التعديل، باستخدام Google Translate (النسخة المجانية بدون API Key)، ويتم
تخزين الترجمة داخل نظام الترجمة الأصلي في أودو (translate=True) - أو في
حقلين جانبيين للنقحرة بالنسبة للأسماء - بحيث يظهر كل مستخدم القيمة بلغته
تلقائيًا في كل الشاشات والتقارير وحقول Many2one.

المميزات:
---------
- شاشة إعدادات (Translation Rules) لاختيار الموديلات والحقول المطلوب ترجمتها.
- وضعين للترجمة: Dictionary (نصوص عامة كالمنتجات) و Transliteration (أسماء أشخاص).
- محرك ترجمة حقيقي (Google Translate) بدل القاموس المحلي البسيط، لجودة أعلى بكثير.
- قاموس استثناءات (Translation Dictionary): الأدمن يقدر يفرض ترجمة معينة
  يدويًا لأي نص (اسم شركة، مصطلح داخلي، تصحيح غلطة من جوجل) قبل ما نكلم جوجل أصلاً.
- كاش دائم لنتايج الترجمة (Translation Cache) لتقليل عدد الطلبات لجوجل
  وتحسين الأداء، مع إمكانية تعديل/مسح أي سطر يديويًا لو الترجمة غلط.
- fallback محلي (نقحرة تقريبية عربي->إنجليزي) لو تعذّر الاتصال بالإنترنت.
- ترجمة فورية عند الإنشاء/التعديل.
- أداة "ترجمة البيانات الموجودة" لترجمة السجلات القديمة على دفعات.

ملاحظة هامة:
------------
الموديول بيستخدم نقطة نهاية غير رسمية مجانية من جوجل (translate.googleapis.com)
ومحتاج اتصال بالإنترنت من السيرفر عشان يشتغل. الخدمة دي مش رسمية من جوجل
وممكن تتغيّر أو يتم إيقافها في أي وقت من غير سابق إنذار.
    """,
    'category': 'Technical',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'product'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/dictionary_seed_data.xml',
        'data/names_dictionary_seed_data.xml',
        'views/translation_rule_views.xml',
        'views/translation_dictionary_views.xml',
        'views/translation_cache_views.xml',
        'wizard/translate_existing_wizard_views.xml',
        'views/menu_views.xml',
        'data/translation_rules_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
