from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

EXPIRING_DAYS = 60


class HrSkillReport(models.Model):
    """Snapshot (rebuilt on open, like hr.employee.data.issue) of the skills of every employee:
    is the skill linked to a certificate, and when does that certificate expire.
    Reads the STANDARD hr_skills data; fields that do not exist in this Odoo build are skipped."""
    _name = 'hr.skill.report'
    _description = 'Employee Skills & Certificates'
    _order = 'company_id, department_id, employee_id, skill_type_id, skill_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', string='Company', index=True)
    department_id = fields.Many2one('hr.department', string='Department')
    skill_type_id = fields.Many2one('hr.skill.type', string='Skill Type', ondelete='set null')
    skill_id = fields.Many2one('hr.skill', string='Skill', ondelete='set null')
    skill_level_id = fields.Many2one('hr.skill.level', string='Level', ondelete='set null')
    level_progress = fields.Integer(string='Progress %')
    is_certification = fields.Boolean(string='Linked to a Certificate')
    valid_from = fields.Date(string='Valid From')
    valid_to = fields.Date(string='Expiry Date')
    days_left = fields.Integer(string='Days Left')
    cert_status = fields.Selection([
        ('no_cert', 'Not a Certificate'),
        ('no_expiry', 'Certificate - No Expiry Date'),
        ('valid', 'Valid'),
        ('expiring', 'Expiring Soon'),
        ('expired', 'Expired'),
    ], string='Certificate Status', index=True)

    @api.model
    def _rebuild(self):
        if 'hr.employee.skill' not in self.env:
            raise UserError(_('The Skills app (hr_skills) is not installed.'))
        Skill = self.env['hr.employee.skill'].sudo()
        fields_ = Skill._fields
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=EXPIRING_DAYS)
        self.sudo().search([]).unlink()
        vals = []
        for rec in Skill.search([]):
            emp = rec.employee_id
            if not emp:
                continue
            skill_type = rec.skill_type_id
            valid_to = rec.valid_to if 'valid_to' in fields_ else False
            valid_from = rec.valid_from if 'valid_from' in fields_ else False
            if 'is_certification' in fields_:
                is_cert = bool(rec.is_certification)
            elif skill_type and 'is_certification' in skill_type._fields:
                is_cert = bool(skill_type.is_certification)
            else:
                is_cert = bool(valid_to)
            if not is_cert:
                status, days = 'no_cert', 0
            elif not valid_to:
                status, days = 'no_expiry', 0
            else:
                days = (valid_to - today).days
                status = 'expired' if valid_to < today else 'expiring' if valid_to <= soon else 'valid'
            vals.append({
                'employee_id': emp.id,
                'company_id': emp.company_id.id,
                'department_id': emp.department_id.id,
                'skill_type_id': skill_type.id,
                'skill_id': rec.skill_id.id,
                'skill_level_id': rec.skill_level_id.id,
                'level_progress': rec.level_progress if 'level_progress' in fields_ else 0,
                'is_certification': is_cert,
                'valid_from': valid_from or False,
                'valid_to': valid_to or False,
                'days_left': days,
                'cert_status': status,
            })
        self.sudo().create(vals)

    @api.model
    def action_open_report(self):
        self._rebuild()
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_management_dashboard.action_skill_report')

    def action_open_employee(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'hr.employee',
            'res_id': self.employee_id.id, 'view_mode': 'form', 'views': [(False, 'form')],
        }
