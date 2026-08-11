# -*- coding: utf-8 -*-
{
    'name': 'Payslip Worked Days Editable Column',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'إظهار عدد أيام العمل كعمود قابل للتعديل مباشرة في ليستة Pay Run Payslips',
    'description': """
Payslip Worked Days Editable Column
=====================================
لو مش رابط جهاز بصمة وبتحدد أيام العمل يدويًا حسب الشيفتات، الموديول ده
بيضيف عمود "أيام العمل" جوه ليستة Pay Run Payslips (الظاهرة لما تفتح
Pay Run وتدوس على الـ Payslips بتاعته)، وتقدر تكتب فيه العدد مباشرة
لكل موظف من غير ما تفتح كل Payslip لوحده.

القيمة بتتكتب فعليًا في سطر "Attendance" بتاع تاب Worked Days جوه كل
Payslip. بعد التعديل، لازم تدوس Compute Sheet عشان المبالغ تتحدث.
    """,
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['hr_payroll'],
    'data': [
        'views/hr_payslip_tree_views.xml',
    ],
    'installable': True,
    'application': False,
}
