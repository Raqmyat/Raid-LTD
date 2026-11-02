from odoo import SUPERUSER_ID, _, api, fields, models

AUDIT_SKIP = {
    'write_date', 'write_uid', 'create_date', 'create_uid', '__last_update',
    'display_name', 'message_main_attachment_id',
}
AUDIT_SKIP_TYPES = ('binary', 'html', 'one2many', 'json', 'properties')


class HrAuditLog(models.Model):
    _name = 'hr.audit.log'
    _description = 'HR User Action Log'
    _order = 'log_date desc, id desc'

    log_date = fields.Datetime(string='Date & Time', default=fields.Datetime.now, index=True, readonly=True)
    log_day = fields.Date(string='Day', default=fields.Date.context_today, index=True, readonly=True)
    user_id = fields.Many2one('res.users', string='User', index=True, readonly=True)
    action = fields.Selection(
        [('create', 'Created'), ('write', 'Updated'), ('unlink', 'Deleted')],
        string='Action', index=True, readonly=True)
    res_model = fields.Char(string='Model (technical)', index=True, readonly=True)
    model_label = fields.Char(string='Module / Model', index=True, readonly=True)
    res_id = fields.Integer(string='Record ID', readonly=True)
    record_name = fields.Char(string='Record', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, readonly=True)
    details = fields.Text(string='What Changed', readonly=True)

    def action_open_record(self):
        self.ensure_one()
        rec = self.env[self.res_model].browse(self.res_id).exists() if self.res_model in self.env else False
        if not rec:
            return {
                'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'message': _('This record no longer exists.'), 'type': 'warning'},
            }
        return {
            'type': 'ir.actions.act_window', 'res_model': self.res_model,
            'res_id': rec.id, 'view_mode': 'form', 'views': [(False, 'form')],
        }


class HrAuditMixin(models.AbstractModel):
    _name = 'hr.audit.mixin'
    _description = 'Logs real user actions (create / write / unlink)'

    def _audit_active(self):
        return not (
            self.env.context.get('hr_audit_off')
            or self.env.uid == SUPERUSER_ID                 # system / cron / OdooBot
            or getattr(self.env.registry, '_init', False)   # module install / update
        )

    def _audit_fields(self, names):
        res = []
        for n in names:
            f = self._fields.get(n)
            if (not f or not f.store or f.type in AUDIT_SKIP_TYPES or n in AUDIT_SKIP
                    or n.startswith(('message_', 'activity_'))):
                continue
            res.append(n)
        return res

    def _audit_fmt(self, rec, fname):
        field = rec._fields[fname]
        val = rec[fname]
        if field.type == 'many2one':
            return val.display_name or ''
        if field.type == 'many2many':
            return ', '.join(val.mapped('display_name'))
        if field.type == 'boolean':
            return _('Yes') if val else _('No')
        if field.type == 'selection':
            return dict(field._description_selection(rec.env)).get(val, val) or ''
        return str(val) if val else ''

    def _audit_vals(self, action, details=''):
        self.ensure_one()
        try:
            name = self.display_name
        except Exception:
            name = str(self.id)
        company = self.company_id if 'company_id' in self._fields else False
        return {
            'user_id': self.env.uid,
            'action': action,
            'res_model': self._name,
            'model_label': self._description or self._name,
            'res_id': self.id,
            'record_name': name,
            'company_id': company.id if company else self.env.company.id,
            'details': details,
        }

    def _audit_create(self, vals_list):
        if vals_list:
            self.env['hr.audit.log'].sudo().with_context(hr_audit_off=True).create(vals_list)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if records and records._audit_active():
            records._audit_create([r._audit_vals('create', _('Record created')) for r in records])
        return records

    def write(self, vals):
        if not self._audit_active():
            return super().write(vals)
        names = self._audit_fields(vals)
        old = {r.id: {n: self._audit_fmt(r, n) for n in names} for r in self} if names else {}
        res = super().write(vals)
        if names:
            logs = []
            for r in self:
                changes = []
                for n in names:
                    new = self._audit_fmt(r, n)
                    before = old[r.id][n]
                    if new != before:
                        changes.append('%s: %s → %s' % (r._fields[n].string, before or '∅', new or '∅'))
                if changes:
                    logs.append(r._audit_vals('write', '\n'.join(changes)))
            self._audit_create(logs)
        return res

    def unlink(self):
        logs = []
        if self._audit_active():
            logs = [r._audit_vals('unlink', _('Record deleted')) for r in self]
        res = super().unlink()
        self._audit_create(logs)
        return res


# --- models whose real user actions are logged -------------------------
class HrEmployee(models.Model):
    _inherit = ['hr.employee', 'hr.audit.mixin']


class HrLeave(models.Model):
    _inherit = ['hr.leave', 'hr.audit.mixin']


class HrLeaveAllocation(models.Model):
    _inherit = ['hr.leave.allocation', 'hr.audit.mixin']


class HrAttendance(models.Model):
    _inherit = ['hr.attendance', 'hr.audit.mixin']


class HrPayslip(models.Model):
    _inherit = ['hr.payslip', 'hr.audit.mixin']
