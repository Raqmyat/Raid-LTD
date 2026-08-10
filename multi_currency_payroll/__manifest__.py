# -*- coding: utf-8 -*-
{
    'name': 'Payroll Multi-Currency (Custom)',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Allow salary contracts and payslips to use a currency different from the company currency',
    'description': """
Payroll Multi-Currency (Odoo 19)
=================================
- مبني على بنية أودو 19 الجديدة اللي فيها hr.contract اتلغى وبقى hr.version.
- يضيف حقل "عملة الراتب" (Salary Currency) على hr.version، قابل للتعديل ومستقل عن عملة الشركة.
- الـ payslip بياخد عملته تلقائي من عملة الـ version المرتبط بيه.
- القيد المحاسبي الناتج عن الـ payslip بيتسجل بعملة الـ version (amount_currency) مع تحويل صحيح لعملة الشركة (سعر الصرف بتاريخ الصرف).

⚠️ لازم قبل التثبيت:
1. تستبدل REPLACE_ME_VIEW_XMLID في views/hr_employee_views.xml بـ external id
   حقيقي لفورم hr.employee اللي فيه تاب Payroll (من Developer Mode).
2. تتأكد إن حقل move_id وحقل contract_id/version_id في hr_payslip.py متطابقين
   مع الموجود فعليًا في قاعدة بياناتك.
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
