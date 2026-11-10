from odoo import api, fields, models


class HrEmployeeSkillReport(models.Model):
    """Report rows rebuilt on opening (same pattern as hr.employee.data.issue).

    Source = the STANDARD skills of the employee (hr.employee.skill, Resume > Skills tab).
    The certification flag and the validity dates are read from the standard fields when this
    Odoo version has them (skill type "certification", employee skill valid from / to);
    otherwise those columns stay empty and nothing breaks.
    """
    _name = 'hr.employee.skill.report'
    _description = 'Employee Skills & Certifications Report'
    _order = 'company_id, department_id, employee_id, skill_type_id, id'

    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', string='Company', index=True)
    department_id = fields.Many2one('hr.department', string='Department')
    skill_type_id = fields.Many2one('hr.skill.type', string='Skill Type')
    skill_id = fields.Many2one('hr.skill', string='Skill')
    skill_level_id = fields.Many2one('hr.skill.level', string='Level')
    level_progress = fields.Integer(string='Progress (%)')
    is_certification = fields.Boolean(string='Certification')
    valid_from = fields.Date(string='Valid From')
    valid_to = fields.Date(string='Certificate Expiry')
    days_left = fields.Integer(string='Days Left')
    expiry_status = fields.Selection([
        ('no_certificate', 'Not a certification'),
        ('no_expiry', 'Certification - no expiry date'),
        ('valid', 'Valid'),
        ('expiring', 'Expiring within 60 days'),
        ('expired', 'Expired'),
    ], string='Certificate Status')

    @api.model
    def _rebuild(self):
        Skill = self.env['hr.employee.skill'].sudo()
        has_dates = 'valid_to' in Skill._fields
        has_from = 'valid_from' in Skill._fields
        has_cert = 'is_certification' in self.env['hr.skill.type']._fields
        today = fields.Date.context_today(self)
        self.sudo().search([]).unlink()
        vals = []
        for line in Skill.search([('employee_id', '!=', False)]):
            emp = line.employee_id
            cert = bool(line.skill_type_id.is_certification) if has_cert else False
            valid_to = line.valid_to if has_dates else False
            if not cert:
                status = 'no_certificate'
            elif not valid_to:
                status = 'no_expiry'
            else:
                left = (valid_to - today).days
                status = 'expired' if left < 0 else ('expiring' if left <= 60 else 'valid')
            vals.append({
                'employee_id': emp.id,
                'company_id': emp.company_id.id,
                'department_id': emp.department_id.id,
                'skill_type_id': line.skill_type_id.id,
                'skill_id': line.skill_id.id,
                'skill_level_id': line.skill_level_id.id,
                'level_progress': line.level_progress,
                'is_certification': cert,
                'valid_from': line.valid_from if has_from else False,
                'valid_to': valid_to or False,
                'days_left': (valid_to - today).days if valid_to else 0,
                'expiry_status': status,
            })
        self.sudo().create(vals)

    @api.model
    def action_open_report(self):
        self._rebuild()
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_management_dashboard.action_employee_skill_report')

    def action_open_employee(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'hr.employee',
            'res_id': self.employee_id.id, 'view_mode': 'form', 'views': [(False, 'form')],
        }
