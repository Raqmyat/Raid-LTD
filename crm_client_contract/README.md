# CRM Client Contracts (Odoo 19)

Service contracts with client companies (payroll / HR administration / PEO / staffing).

* CRM > Contracts > Client Contracts (list / kanban / pivot / graph / form), "Contracts to Renew".
* Alerts (daily cron "Client Contracts: expiry status + alerts"): inbox/email message to the account manager,
  the "Also Notify" users and the followers at [alert days] (default 60), then 30 / 15 / 7 days and on expiry.
  The account manager also gets a to-do. Default alert days: system parameter
  `crm_client_contract.default_notice_days`.
* Renew button: wizard creates the next term (running) and marks the old one "Renewed". With "Auto-Renew"
  the cron creates the next term itself after the end date.
* Groups: Client Contracts / Viewer (read), User (create/edit), Manager (all). CRM salesmen = User,
  CRM managers = Manager, HR managers = Viewer. Give "Viewer" to anyone who must receive the alerts.
* Reports live in `hr_management_dashboard` (HR Reports > Clients > Client Contracts Expiry).
