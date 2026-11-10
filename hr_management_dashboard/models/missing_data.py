from odoo import api, fields, models

# employee fields that must be filled; fields not existing in this DB are skipped
CHECK_FIELDS = [
    'identification_id', 'passport_id', 'birthday', 'gender', 'country_id',
    'place_of_birth', 'marital', 'private_street', 'private_phone', 'private_email',
    'work_email', 'mobile_phone', 'emergency_contact', 'emergency_phone',
    'bank_account_id', 'department_id', 'job_id', 'parent_id',
]
LABEL_OVERRIDE = {'identification_id': 'Identification No (ID)'}
# field -> field that must be filled first (only checked when that one is set)
CONDITIONAL_FIELDS = {'identification_expire': 'identification_id'}


class HrEmployeeDataIssue(models.Model):
    _name = 'hr.employee.data.issue'
    _description = 'Employee Missing Data'
    _order = 'company_id, department_id, employee_id, id'

    employee_id = fields.Many2one('hr.employee', string='Employee', ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', string='Company', index=True)
    department_id = fields.Many2one('hr.department', string='Department')
    field_name = fields.Char(string='Field (technical)')
    issue = fields.Char(string='Missing Data')

    @api.model
    def _rebuild(self):
        Employee = self.env['hr.employee'].sudo()
        self.sudo().search([]).unlink()
        names = [n for n in CHECK_FIELDS + list(CONDITIONAL_FIELDS) if n in Employee._fields]
        labels = Employee.fields_get(names, attributes=['string'])
        vals = []
        for emp in Employee.search([]):
            for n in names:
                if n in CONDITIONAL_FIELDS and not emp[CONDITIONAL_FIELDS[n]]:
                    continue
                v = emp[n]
                missing = (not v.strip()) if isinstance(v, str) else (not v)
                if missing:
                    vals.append({
                        'employee_id': emp.id,
                        'company_id': emp.company_id.id,
                        'department_id': emp.department_id.id,
                        'field_name': n,
                        'issue': LABEL_OVERRIDE.get(n, labels[n]['string']),
                    })
        self.sudo().create(vals)

    @api.model
    def action_open_report(self):
        self._rebuild()
        return self.env['ir.actions.act_window']._for_xml_id(
            'hr_management_dashboard.action_employee_data_issue')

    def action_open_employee(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'res_model': 'hr.employee',
            'res_id': self.employee_id.id, 'view_mode': 'form', 'views': [(False, 'form')],
        }
