# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrPayslipInput(models.Model):
    """Extends the STANDARD Odoo model (the real 'Other Inputs' lines on a
    payslip), only to make each line's tag label show 'Type: Amount'
    (e.g. 'Actual Basic: 900.0') when displayed with widget="many2many_tags".
    """
    _inherit = 'hr.payslip.input'

    def _compute_display_name(self):
        for rec in self:
            label = rec.input_type_id.name or rec.name or 'Input'
            rec.display_name = '%s: %s' % (label, rec.amount)
