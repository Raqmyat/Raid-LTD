# -*- coding: utf-8 -*-
{
    'name': 'Sale/Purchase Employee Salaries',
    'version': '19.0.1.2.0',
    'category': 'Sales',
    'summary': 'ربط أوامر البيع/الشراء بالموظفين، وطباعة جدول تفصيل الرواتب (Employee x Rule) في أمر البيع والفاتورة',
    'description': """
Sale/Purchase Employee Salaries
=================================
- Checkbox "Is Salaries?" على أمر البيع (وبيتوّرث للفاتورة تلقائيًا عند الفوترة).
- حقل "Employee" على بنود أمر البيع وأمر الشراء.
- زرار "توليد بنود المرتبات" يظهر بس لو Is Salaries مفعّل، بيفتح ويزارد:
  1. تختار المنتج (مثلاً منتج اسمه Salary) والباتش (Pay Run) بتاع الشهر.
  2. بيحمّل تلقائي سطر واحد لكل موظف بإجمالي تكلفته (Employer Cost)، وتقدر
     تعدل القيمة أو تستبعد أي موظف.
  3. تدوس "توليد البنود" فيتضاف سطر واحد بسيط لكل موظف (زي أي بند بيع عادي).
- عند الطباعة (أمر البيع أو الفاتورة)، لو Is Salaries مفعّل، بيظهر في آخر
  الصفحة جدول تفصيلي منفصل: كل موظف = صف، وكل رول من رولز الراتب (حتى
  تكلفة الموظف) = عمود - للعرض فقط، مش بنود فعلية بتأثر على الحسابات.
    """,
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['sale', 'purchase', 'hr', 'hr_payroll', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_order_salary_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        'report/sale_order_report.xml',
        'report/invoice_report.xml',
    ],
    'installable': True,
    'application': False,
}
