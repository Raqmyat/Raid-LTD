# -*- coding: utf-8 -*-
{
    'name': 'Raid Custom Sales and Purchase Approval Workflow',
    'version': '19.0.1.0',
    'category': 'Operations',
    'summary': 'Parallel multi-level approval cycle for Sales and Purchases with PO wizard.',
    'description': """
        This module implements a specific approval workflow for Sales and Purchase orders:
        Sales: Draft -> Submitted -> Op Manager -> HR -> Audit -> CEO -> Sale (Full Cycle),
               or Draft -> Submitted -> Finance -> Sale (Finance Cycle).
        Purchase: Draft -> Submitted -> Op Manager -> HR -> (Approve & Close, or Legal -> Finance -> Audit -> CEO) -> Purchase.
        Each company independently chooses which cycle (if any) applies via a field on the
        company card / Settings. Includes a wizard to create POs from SOs.
    """,
    'author': 'Eng/Mohamed elgarhy',
    'depends': ['sale', 'purchase', 'mail'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/create_po_wizard_view.xml',
        'views/res_config_settings_views.xml',
        'views/res_company_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
}
