{
    'name': 'Payroll Batch Custom - Days Worked & Batch Payment',
    'version': '19.0.1.0.0',
    'summary': 'ويزارد لتحديد أيام العمل عند التوليد + ترحيل تلقائي لقيد اليومية بعد الاعتماد + زرار دفع جماعي '
               'بيومية واحدة مع تسجيل كل عملية سداد بشكل منفصل لكل Payslip',
    'description': """
Payroll Batch Custom
=====================
1. عند توليد رواتب الباتش: يفتح ويزارد لتحديد عدد أيام العمل لكل موظف يدويًا (بدون الحاجة لجهاز البصمة).
2. عند اعتماد (Validate) الباتش: يتم Post تلقائي لقيد اليومية الخاص بكل Payslip تم توليده.
3. زرار "Pay" في صفحة الباتش: يفتح ويزارد لاختيار الموظفين ويومية دفع واحدة، وعند التأكيد يتم إنشاء
   سند دفع منفصل لكل Payslip (وليس قيد دفع واحد مجمّع) تمامًا كما لو تم الدفع يدويًا لكل واحد على حدة.

ملاحظة مهمة: هذا الموديول مبني على افتراض أنك تستخدم hr_payroll Enterprise (فيه حقل move_id على hr.payslip
وربط محاسبي فعلي). راجع حقل state على hr.payslip.run في وضع المطور وعدّل القيم في models/hr_payslip_run.py
(closing_states) لتطابق القيمة الفعلية التي تُخزَّن بعد الضغط على Validate عندك.
    """,
    'category': 'Human Resources/Payroll',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['hr_payroll', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizards/hr_payslip_run_generate_wizard_views.xml',
        'wizards/hr_payslip_run_pay_wizard_views.xml',
        'views/hr_payslip_run_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
