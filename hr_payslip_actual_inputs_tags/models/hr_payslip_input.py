# -*- coding: utf-8 -*-
from odoo import models


class HrPayslipInput(models.Model):
    """Extends the STANDARD Odoo model (the real 'Other Inputs' lines on a
    payslip). Only adds a readable tag label ('Type: Amount') so it displays
    nicely when shown with widget="many2many_tags" in the Payslips list.
    No new model, no new table - this is the same data Salary Rules already
    read via inputs.CODE.amount.
    """
    _inherit = 'hr.payslip.input'

    def _compute_display_name(self):
        for rec in self:
            label = rec.input_type_id.name or rec.name or 'Input'
            rec.display_name = '%s: %s' % (label, rec.amount)
