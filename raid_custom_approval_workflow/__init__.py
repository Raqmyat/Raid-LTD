# -*- coding: utf-8 -*-
from . import models
from . import wizard


def post_init_hook(env):
    """Carry over the old global on/off switches (ir.config_parameter) to
    the new per-company fields, so companies that already had the cycle
    enabled before this update keep working exactly as before. New
    installs simply keep every company on 'none' (no approval cycle)."""
    get_param = env['ir.config_parameter'].sudo().get_param
    sale_was_enabled = bool(get_param('raid_custom_approval_workflow.use_sale_approval_cycle'))
    purchase_was_enabled = bool(get_param('raid_custom_approval_workflow.use_purchase_approval_cycle'))

    if not sale_was_enabled and not purchase_was_enabled:
        return

    values = {}
    if sale_was_enabled:
        values['sale_approval_cycle_type'] = 'full'
    if purchase_was_enabled:
        values['purchase_approval_cycle_type'] = 'full'

    env['res.company'].sudo().search([]).write(values)
