# -*- coding: utf-8 -*-
{
    'name': 'Payroll Multi-Currency (Custom)',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Allow salary contracts and payslips to use a currency different from the company currency',
    'description': """
Salary Currency Helper (Odoo 19)
==================================
مش بيغيّر عملة الحساب أو القيود المحاسبية خالص - كل حاجة بتفضل بعملة الشركة.

- كارت الموظف: حقل "عملة راتب الموظف" بس (تحديد العملة، من غير أي تحويل هنا).
- وأنت بتعمل Payslip: هيظهرلك حقل "الراتب بالعملة التانية" بجانب عملة
  الموظف. تكتب فيه المبلغ بتاع الشهر ده، وهو اللي هيعمل Override تلقائي
  لحقل الراتب الأساسي (Wage) بتاع الموظف بالمعادل بعملة الشركة (بسعر
  الصرف بتاريخ بداية الفترة)، وعليه هيتم كل حساب البايرول عادي.
- لو العملة زي عملة الشركة، مفيش أي تأثير خالص - كل حاجة بتشتغل عادي.
    """,
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': [
        'hr_payroll',
        'hr_payroll_account',
        'account',
    ],
    'data': [
        'views/hr_employee_views.xml',
        'views/hr_payslip_views.xml',
    ],
    'installable': True,
    'application': False,
}
