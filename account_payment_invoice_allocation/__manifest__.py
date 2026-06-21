# -*- coding: utf-8 -*-
{
    'name': 'Account Payment Invoice Allocation',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Explicit invoice allocation management during payment creation',
    'description': """
Account Payment Invoice Allocation
===================================
This module extends Customer Payments and Vendor Payments to require
explicit allocation of payment amounts to one or more invoices/bills,
or to register the payment as an advance payment with no invoice
allocation.

Features
--------
* Allocation Type: Invoice Payment / Advance Payment
* Multi-invoice allocation with Fixed Amount or Percentage methods
* Automatic two-way recalculation between amount and percentage
* Validation against over-allocation and duplicate invoice selection
* Allocation records are stored at posting time without forcing
  reconciliation
* "Allocated Invoices" smart button on the payment form
* "Apply Allocations" action to reconcile the payment against the
  stored allocations using Odoo's standard reconciliation engine,
  which automatically supports both partial and full reconciliation
""",
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
