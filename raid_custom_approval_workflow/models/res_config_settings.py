# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    use_sale_approval_cycle = fields.Boolean(
        string="Use Sales Approval Cycle",
        config_parameter='raid_custom_approval_workflow.use_sale_approval_cycle'
    )
    use_purchase_approval_cycle = fields.Boolean(
        string="Use Purchase Approval Cycle",
        config_parameter='raid_custom_approval_workflow.use_purchase_approval_cycle'
    )
