# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    actual_input_note = fields.Char(
        string='Actual Inputs Status',
        compute='_compute_actual_input_note',
        help='Shows whether there are any "Actual Salary Inputs" rows for '
             'this employee and month, which will be automatically added '
             'to the Other Inputs tab when you press Compute Sheet.',
    )

    @api.depends('employee_id', 'date_from')
    def _compute_actual_input_note(self):
        for slip in self:
            recs = slip._get_actual_input_records()
            if recs:
                names = ', '.join(recs.mapped('input_type_id.name'))
                slip.actual_input_note = 'Will add: %s' % names
            else:
                slip.actual_input_note = ''

    def _get_actual_input_records(self):
        """Return all 'Actual Salary Inputs' rows (any Input Type) for the
        same employee and the same month as this payslip."""
        self.ensure_one()
        if not self.employee_id or not self.date_from:
            return self.env['hr.payslip.actual.input']
        return self.env['hr.payslip.actual.input'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '=', self.date_from.replace(day=1)),
        ])

    def compute_sheet(self):
        for slip in self:
            slip._sync_actual_inputs_to_payslip()
        return super().compute_sheet()

    def _sync_actual_inputs_to_payslip(self):
        """Push every matching row from the standalone Actual Salary Inputs
        table (hr.payslip.actual.input) for this employee/month into this
        payslip's real Other Inputs lines (hr.payslip.input), so any Salary
        Rule can read them the normal Odoo way via inputs.CODE.amount, with
        no custom lookup code needed.
        If a line with the same Input Type already exists on this payslip,
        only its amount is updated (never duplicated).
        """
        self.ensure_one()
        actual_inputs = self._get_actual_input_records()
        for rec in actual_inputs:
            line = self.input_line_ids.filtered(
                lambda l: l.input_type_id == rec.input_type_id)
            if line:
                line[0].amount = rec.amount
            else:
                self.env['hr.payslip.input'].create({
                    'payslip_id': self.id,
                    'input_type_id': rec.input_type_id.id,
                    'amount': rec.amount,
                    'name': rec.note or rec.input_type_id.name,
                })
