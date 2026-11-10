{
    'name': 'CRM Client Contracts',
    'version': '19.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Service contracts signed with client companies (payroll / HR outsourcing) '
               'with start / end dates, renewal and expiry alerts',
    'description': """
Client service contracts, recorded inside the CRM.

* Contract per client (partner) with start / end date, type of service, fees, headcount,
  payroll cycle, notice period, auto-renewal and the client company in the HR system.
* Expiry alerts: a daily cron notifies the account manager, the extra "Notify Users" and the
  followers (inbox / email + an activity for the account manager) when the contract gets close
  to its end date (configurable days before the end, then 30 / 15 / 7 days, then when expired).
* Renewal wizard: creates the next term and closes the old one.
* Smart button on the opportunity.
""",
    'depends': ['crm', 'mail', 'hr'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'data/service_data.xml',
        'data/cron_data.xml',
        'views/client_contract_views.xml',
        'views/crm_lead_views.xml',
        'wizard/renew_wizard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
