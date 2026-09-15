# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Each company decides on its own whether to use an approval cycle at
    # all, and - for Sales - which cycle to use. New cycles can be added
    # later just by adding another option here + the matching logic on
    # sale.order, without touching companies that already picked one.
    sale_approval_cycle_type = fields.Selection(
        selection=[
            ('none', 'No Approval Cycle'),
            ('full', 'Full Cycle (Ops Manager → HR → Audit → CEO)'),
            ('finance', 'Finance Cycle (Finance Approval Only)'),
        ],
        string='Sales Approval Cycle',
        default='none',
        required=True,
        help="Which sales approval cycle (if any) applies to Sales Orders "
             "created in this company.",
    )
    purchase_approval_cycle_type = fields.Selection(
        selection=[
            ('none', 'No Approval Cycle'),
            ('full', 'Full Cycle'),
        ],
        string='Purchase Approval Cycle',
        default='none',
        required=True,
        help="Which purchase approval cycle (if any) applies to Purchase "
             "Orders created in this company.",
    )
