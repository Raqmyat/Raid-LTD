# -*- coding: utf-8 -*-
{
    'name': 'Raid Custom Sales and Purchase Approval Workflow',
    'version': '19.0.1.0',
    'category': 'Operations',
    'summary': 'Parallel multi-level approval cycle for Sales and Purchases with PO wizard.',
    'description': """
        This module implements a specific approval workflow for Sales and Purchase orders:
        Sales: Draft -> Submitted -> Op Manager -> HR -> Audit -> CEO -> Sale.
        Purchase: Draft -> Submitted -> Op Manager -> HR -> Legal -> Finance -> Audit -> CEO -> Purchase.
        Includes a wizard to create POs from SOs and a configuration to toggle the cycle.
    """,
    'author': 'Eng/Mohamed elgarhy',
    # NOTE: 'hr_payroll' is the standard Odoo payroll module technical name.
    # If your installation uses a different payroll app/technical name
    # (custom or OCA), change this dependency accordingly.
    'depends': ['sale', 'purchase', 'mail', 'hr_payroll'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/create_po_wizard_view.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
    ],
    'installable': True,
    'application': True,
}
