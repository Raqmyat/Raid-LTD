# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Company-dependent settings: res.config.settings automatically reads
    # from / writes to the currently selected company (company_id) through
    # these related fields, so each company can pick its own cycle.
    sale_approval_cycle_type = fields.Selection(
        related='company_id.sale_approval_cycle_type',
        string='Sales Approval Cycle',
        readonly=False,
    )
    purchase_approval_cycle_type = fields.Selection(
        related='company_id.purchase_approval_cycle_type',
        string='Purchase Approval Cycle',
        readonly=False,
    )
