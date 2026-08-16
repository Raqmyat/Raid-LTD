# -*- coding: utf-8 -*-
{
    'name': 'Sale/Purchase Employee Salaries',
    'version': '19.0.1.1.0',
    'category': 'Sales',
    'summary': 'ربط أوامر البيع/الشراء بالموظفين وتوليد بنود المرتبات تلقائيًا من البايرول (تفصيلي أو إجمالي)',
    'description': """
Sale/Purchase Employee Salaries
=================================
- Checkbox "Is Salaries?" على أمر البيع.
- حقل "Employee" على بنود أمر البيع وأمر الشراء (اختياري دايمًا، مش بس لما
  يبقى Is Salaries مفعّل).
- زرار "توليد بنود المرتبات" يظهر لما Is Salaries مفعّل، بيفتح ويزارد:
  1. تختار المنتج والباتش (Pay Run) بتاع الشهر من البايرول.
  2. تختار طريقة التوليد: تفصيلي (بند منفصل لكل عنصر أجر/رول لكل موظف)
     أو إجمالي (بند واحد لكل موظف بإجمالي التكلفة).
  3. تحمّل البنود تلقائي، وتقدر تعدل القيمة أو تستبعد أي بند.
  4. تدوس "توليد البنود" فيتضاف سطر لكل بند مُعلّم بنفس المنتج.
- الموظف بيتوّرث تلقائيًا من بند أمر البيع لبند الفاتورة عند الفوترة.
- الموظف بيتطبع في تقرير أمر البيع وفي تقرير الفاتورة.
    """,
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['sale', 'purchase', 'hr', 'hr_payroll', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_order_salary_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'report/sale_order_report.xml',
        'report/invoice_report.xml',
    ],
    'installable': True,
    'application': False,
}
