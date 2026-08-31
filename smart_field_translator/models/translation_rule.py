# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools


class TranslationRule(models.Model):
    _name = 'translation.rule'
    _description = 'قاعدة الترجمة التلقائية لحقل في موديل معيّن'
    _rec_name = 'model_id'

    model_id = fields.Many2one(
        'ir.model', string='الموديل (Model)', required=True, ondelete='cascade',
        domain=[('transient', '=', False)],
    )
    model_name = fields.Char(related='model_id.model', store=True, readonly=True, string='Technical Name')
    field_ids = fields.Many2many(
        'ir.model.fields', string='الحقول المطلوب ترجمتها',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['char', 'text'])]",
        help='في وضع Dictionary لازم الحقل يكون Translatable (translate=True). '
             'في وضع Transliteration الحقل يفضل زي ما هو، وبيتحط جانبه '
             'تلقائيًا حقلين <field>_ar و <field>_en (لازم تكون متعرّفة '
             'على الموديل مسبقًا عن طريق _inherit).',
    )
    translate_mode = fields.Selection([
        ('dictionary', 'ترجمة عامة (Dictionary) - مناسب للمنتجات، الفئات، إلخ'),
        ('transliteration', 'نقحرة أسماء أشخاص (Transliteration) - مناسب للموظفين، جهات الاتصال'),
    ], string='طريقة الترجمة', default='dictionary', required=True)
    active = fields.Boolean(default=True)
    note = fields.Text(string='ملاحظات', help='أي ملاحظات إضافية عن هذه القاعدة.')

    _sql_constraints = [
        ('model_uniq', 'unique(model_id)', 'يوجد بالفعل إعداد ترجمة لهذا الموديل!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    @api.model
    @tools.ormcache()
    def _get_translation_map(self):
        """يرجع dict: { model_technical_name: {'fields': [...], 'mode': 'dictionary'|'transliteration'} }"""
        rules = self.sudo().search([('active', '=', True)])
        result = {}
        for rule in rules:
            if not rule.model_name or not rule.field_ids:
                continue
            result[rule.model_name] = {
                'fields': rule.field_ids.mapped('name'),
                'mode': rule.translate_mode,
            }
        return result
