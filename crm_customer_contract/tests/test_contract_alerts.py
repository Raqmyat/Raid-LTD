from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestContractAlerts(TransactionCase):

    def _contract(self, months_left, days=0):
        today = fields.Date.context_today(self.env.user)
        return self.env['crm.customer.contract'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Customer'}).id,
            'date_start': today - relativedelta(years=1),
            'date_end': today + relativedelta(months=months_left, days=days),
        })

    def _alerts(self, contract):
        atype = self.env.ref('crm_customer_contract.mail_activity_type_contract_expiry')
        return contract.activity_ids.filtered(lambda a: a.activity_type_id == atype)

    def test_stages_once_each(self):
        c = self._contract(months_left=2, days=-1)   # inside the 2-month stage
        c.action_confirm()
        self.assertEqual(c.alert_stage, 2)
        n = len(self._alerts(c))
        self.assertTrue(n)
        c._send_expiry_alerts()                       # same stage again: nothing new
        self.assertEqual(len(self._alerts(c)), n)

    def test_too_early_and_renewal_reset(self):
        c = self._contract(months_left=6)
        c.action_confirm()
        self.assertEqual(c.alert_stage, 0)
        self.assertFalse(self._alerts(c))
        c.date_end = fields.Date.context_today(self.env.user) + relativedelta(days=10)
        self.assertEqual(c.alert_stage, 0)            # changed end date restarts the alerts
        c._send_expiry_alerts()
        self.assertEqual(c.alert_stage, 1)

    def test_cron_expires(self):
        c = self._contract(months_left=0, days=-5)
        c.state = 'running'
        self.env['crm.customer.contract']._cron_contract_expiry()
        self.assertEqual(c.state, 'expired')
