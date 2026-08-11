# -*- coding: utf-8 -*-
{
    'name': 'Sale/Purchase Employee Salaries',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'ربط أوامر البيع/الشراء بالموظفين وتوليد بنود المرتبات تلقائيًا من البايرول',
    'description': """
Sale/Purchase Employee Salaries
=================================
- Checkbox "Is Salaries?" على أمر البيع.
- حقل "Employee" على بنود أمر البيع وأمر الشراء (اختياري دايمًا، مش بس لما
  يبقى Is Salaries مفعّل).
- زرار "توليد بنود المرتبات" يظهر لما Is Salaries مفعّل، بيفتح ويزارد:
  1. تختار المنتج والباتش (Pay Run) بتاع الشهر من البايرول.
  2. تحمّل الموظفين المسجلين في الباتش ده، وبيظهرلك المبلغ الإجمالي
     المدفوع لكل موظف (مش بس الصافي - شامل كل البنود)، وتقدر تعدله يدويًا.
  3. تختار مين هتضيفه، وتدوس "توليد البنود" فيتضاف سطر لكل موظف بنفس
     المنتج وبسعر المبلغ اللي حددته.
- الموظف بيتطبع في تقرير أمر البيع.
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
    ],
    'installable': True,
    'application': False,
}
