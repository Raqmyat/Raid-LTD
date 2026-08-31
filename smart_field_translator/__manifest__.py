# -*- coding: utf-8 -*-
{
    'name': 'Smart Field Auto Translator',
    'version': '19.0.1.0.0',
    'summary': 'ترجمة تلقائية لأي حقل نصي (موظفين، منتجات، ...) حسب لغة النظام - بدون API مدفوعة',
    'description': """
Smart Field Auto Translator
============================
يسمح للأدمن بتحديد أي موديل وأي حقل (يجب أن يكون translate=True) ليتم
ترجمته تلقائيًا فور الإنشاء أو التعديل، باستخدام محرك ترجمة محلي مجاني
(قاموس + transliteration للأسماء الشخصية)، ويتم تخزين الترجمة داخل نظام
الترجمة الأصلي في أودو (translate=True) بحيث يظهر كل مستخدم القيمة بلغته
تلقائيًا في كل الشاشات والتقارير وحقول Many2one.

المميزات:
---------
- شاشة إعدادات (Translation Rules) لاختيار الموديلات والحقول المطلوب ترجمتها.
- وضعين للترجمة: Dictionary (نصوص عامة كالمنتجات) و Transliteration (أسماء أشخاص).
- قاموس مصطلحات (Translation Dictionary) قابل للتوسع من واجهة المستخدم.
- ترجمة فورية عند الإنشاء/التعديل.
- أداة "ترجمة البيانات الموجودة" لترجمة السجلات القديمة على دفعات.
- لا يحتاج أي API Key أو اتصال إنترنت.
    """,
    'category': 'Technical',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/dictionary_seed_data.xml',
        'views/translation_rule_views.xml',
        'views/translation_dictionary_views.xml',
        'wizard/translate_existing_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
