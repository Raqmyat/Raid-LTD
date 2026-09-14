# -*- coding: utf-8 -*-
{
    'name': 'Auto Translate Names via DeepL (AR/EN)',
    'version': '1.0',
    'summary': 'ترجمة تلقائية (عربي/إنجليزي) لاسم المورد/العميل والموظف والمنتج '
               'وحساب دليل الحسابات باستخدام DeepL API المجاني',
    'description': """
عند إنشاء أو تعديل اسم في:
    - الموردين والعملاء (res.partner)
    - الموظفين (hr.employee)
    - المنتجات (product.template)
    - شجرة الحسابات (account.account)
    - دفاتر اليومية (account.journal)

المديول بيكتشف تلقائيًا هل الاسم عربي ولا إنجليزي، ويترجمه للغة التانية
عن طريق DeepL API (الخطة المجانية)، ويخزّن الترجمة باستخدام آلية أودو
الأصلية للحقول القابلة للترجمة (translate=True) - فتظهر النسخة الصح
تلقائيًا حسب لغة المستخدم/النظام.

- لو فيه ترجمة يدوية موجودة بالفعل لسجل معيّن، المديول ميلمسهاش
  (بيفترض إنها اتظبطت يدوي ومقصودة).
- أي فشل في الاتصال بـ DeepL (مفتاح غلط / انترنت / حد الاستخدام) بيتسجل
  في الـ log وبيتجاهل بأمان، ومبيوقفش حفظ السجل أبدًا.

الإعداد:
    فعّل Developer Mode، روح لـ Settings > Technical > Parameters >
    System Parameters، أنشئ Parameter جديد:
        Key:   auto_translate_deepl.api_key
        Value: مفتاح DeepL API بتاعك (لازم ينتهي بـ :fx لو حساب مجاني)
    """,
    'category': 'Localization',
    'author': 'Custom',
    'depends': ['base', 'contacts', 'hr', 'product', 'account'],
    'external_dependencies': {'python': ['requests']},
    'installable': True,
    'application': False,
    'auto_install': False,
}
