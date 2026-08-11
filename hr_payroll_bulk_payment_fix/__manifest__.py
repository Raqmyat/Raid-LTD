# -*- coding: utf-8 -*-
{
    'name': 'HR Payroll Bulk Payment Fix',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'إصلاح خطأ "Expected singleton" عند تسجيل دفع لأكتر من Payslip مربوطين بنفس القيد المحاسبي',
    'description': """
HR Payroll Bulk Payment Fix
=============================
مشكلة معروفة في hr_payroll_account: لما أكتر من Payslip يبقوا مرتبطين
بنفس القيد المحاسبي (زي لما يتفعّل خيار "Batch Account Move Lines")،
وتحاول تسجل دفع (Register Payment) عليهم، الكود بيحاول يعمل message_post
على كل الـ Payslips دي مرة واحدة كـ recordset واحد، وده بيفشل لأن
message_post محتاج سجل واحد بس (ensure_one)، فبيظهر الخطأ:

    ValueError: Expected singleton: hr.payslip(...)

الموديول ده بيعالج المشكلة دي بس - بيخلي hr.payslip تتقبل message_post
على أكتر من سجل، وتلف عليهم واحد واحد بدل ما ترمي Error.

مفيش أي تغيير تاني في السلوك - الموديول ده معزول تمامًا وممكن تركبه
لوحده من غير أي اعتماد على موديولات تانية عملناها.
    """,
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['hr_payroll_account'],
    'data': [],
    'installable': True,
    'application': False,
}
