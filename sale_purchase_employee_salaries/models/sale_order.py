# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_salaries = fields.Boolean(
        string='Is Salaries?',
        help='فعّل الخيار ده لو الأوردر ده بيمثل تحميل تكلفة مرتبات على العميل/الجهة.',
    )

    def action_open_salary_wizard(self):
        self.ensure_one()
        return {
            'name': 'توليد بنود المرتبات',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.salary.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }
