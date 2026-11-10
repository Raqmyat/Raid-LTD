from odoo import api, fields, models


class HrPayslipBillingStatus(models.Model):
    """Snapshot (rebuilt on open, like hr.employee.data.issue) of the billing status of every
    payslip that belongs to a batch, so it can be grouped / pivoted by batch, company, status."""
    _name = 'hr.payslip.billing.status'
    _description = 'Payslip Billing Status'
    _order = 'date_from desc, payslip_run_id, employee_id'

    slip_id = fields.Many2one('hr.payslip', string='Payslip', ondelete='cascade', index=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', string='Company', index=True)
    department_id = fields.Many2one('hr.department', string='Department')
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Pay Run', ondelete='cascade', index=True)
    slip_state = fields.Selection(related='slip_id.state', string='Payslip Status', store=True, index=True)
    date_from = fields.Date(string='Period From')
    date_to = fields.Date(string='Period To')
    billing_status = fields.Selection(
        [('none', 'No Sale Order'),
         ('ordered', 'Sale Order - Not Invoiced'),
         ('invoiced', 'Invoiced')], string='Billing Status', index=True)
    billable_amount = fields.Float(string='Billable Amount')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_payment_state = fields.Selection(related='invoice_id.payment_state', string='Payment')

    @api.model
    def _rebuild(self):
        Slip = self.env['hr.payslip'].sudo()
        self.sudo().search([]).unlink()
        slips = Slip.search([('payslip_run_id', '!=', False)])
        docs = Slip._get_billing_docs(slips)
        vals = []
        for slip in slips:
            doc = docs.get((slip.payslip_run_id.id, slip.employee_id.id))
            orders = doc['orders'] if doc else self.env['sale.order']
            invoices = doc['invoices'] if doc else self.env['account.move']
            vals.append({
                'slip_id': slip.id,
                'employee_id': slip.employee_id.id,
                'company_id': slip.company_id.id,
                'department_id': slip.employee_id.department_id.id,
                'payslip_run_id': slip.payslip_run_id.id,
                'date_from': slip.date_from,
                'date_to': slip.date_to,
                'billing_status': 'invoiced' if invoices else ('ordered' if orders else 'none'),
                'billable_amount': slip._get_billable_amount(),
                'sale_order_id': orders[:1].id,
                'invoice_id': invoices[:1].id,
            })
        self.sudo().create(vals)

    @api.model
    def action_open_report(self):
        self._rebuild()
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_management_dashboard.action_payslip_billing_status')

    def action_open_payslip(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'hr.payslip',
            'res_id': self.slip_id.id, 'view_mode': 'form', 'views': [(False, 'form')],
        }
