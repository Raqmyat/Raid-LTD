# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .utils import auto_translate_field


class ResPartner(models.Model):
    _inherit = 'res.partner'

    name = fields.Char(translate=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get('skip_auto_translate'):
            for record in records:
                auto_translate_field(self.env, record, 'name')
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals and not self.env.context.get('skip_auto_translate'):
            for record in self:
                auto_translate_field(self.env, record, 'name')
        return res
