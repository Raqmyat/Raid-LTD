# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

BATCH_SIZE = 200


class TranslateExistingWizard(models.TransientModel):
    _name = 'translate.existing.wizard'
    _description = 'ترجمة البيانات الموجودة بالفعل'

    rule_ids = fields.Many2many(
        'translation.rule', string='القواعد المطلوب تطبيقها',
        default=lambda self: self.env['translation.rule'].search([('active', '=', True)]),
    )
    overwrite_existing = fields.Boolean(
        string='استبدال الترجمات الموجودة بالفعل',
        help='لو مفعّل، هيعيد توليد الترجمة حتى لو كانت موجودة بالفعل. '
             'لو غير مفعّل، هيترجم فقط السجلات اللي ناقصة ترجمة.',
    )
    result_message = fields.Text(string='النتيجة', readonly=True)

    def action_translate_now(self):
        self.ensure_one()
        total_translated = 0
        total_records = 0
        summary_lines = []

        for rule in self.rule_ids:
            if not rule.model_name or not rule.field_ids:
                continue
            Model = self.env[rule.model_name].sudo()
            if not Model._name:
                continue

            domain = []
            record_ids = Model.with_context(active_test=False).search(domain).ids
            model_translated = 0

            for offset in range(0, len(record_ids), BATCH_SIZE):
                batch_ids = record_ids[offset:offset + BATCH_SIZE]
                records = Model.browse(batch_ids)
                try:
                    records._auto_translate_fields(
                        only_fields=rule.field_ids.mapped('name'),
                        force=self.overwrite_existing,
                    )
                    model_translated += len(batch_ids)
                    self.env.cr.commit()  # noqa: commit مقصود عشان نتفادى timeout على بيانات كبيرة
                except Exception:
                    _logger.exception('فشل ترجمة دفعة من %s', rule.model_name)
                    self.env.cr.rollback()

            total_translated += model_translated
            total_records += len(record_ids)
            summary_lines.append(
                f'- {rule.model_id.name} ({rule.model_name}): تمت معالجة {model_translated} سجل.'
            )

        self.result_message = (
            f'تمت معالجة {total_translated} من أصل {total_records} سجل.\n\n'
            + '\n'.join(summary_lines)
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'translate.existing.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
