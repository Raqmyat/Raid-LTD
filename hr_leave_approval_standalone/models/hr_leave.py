from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
from lxml import etree


APPROVAL_STATES = [
    ('draft', 'Draft'),
    ('submitted', 'Waiting for Manager'),
    ('manager_approved', 'Manager Approved'),
    ('hr_approved', 'HR Approved'),
    ('cfo', 'Waiting for CFO'),
    ('ceo', 'Waiting for CEO'),
    ('done', 'Closed'),
    ('refused', 'Refused'),
]


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    approval_state = fields.Selection(
        APPROVAL_STATES, string='Approval Status', default='draft', copy=False,
        tracking=True, index=True, readonly=True)

    def _approval_exempt(self):
        return self.filtered(lambda leave: getattr(leave, 'validation_type', False) == 'no_validation')

    def _approval_is_hr(self):
        return self.env.user.has_group('hr_holidays.group_hr_user') or self.env.user.has_group('hr_holidays.group_hr_manager')

    def _approval_is_cfo(self):
        return self.env.user.has_group('hr_leave_approval_standalone.group_leave_approval_cfo')

    def _approval_is_ceo(self):
        return self.env.user.has_group('hr_leave_approval_standalone.group_leave_approval_ceo')

    def _approval_is_manager(self):
        self.ensure_one()
        manager_user = self.employee_id.parent_id.user_id
        return bool(manager_user and manager_user == self.env.user)

    def _approval_check(self, allowed, role):
        for leave in self:
            if leave.approval_state not in allowed:
                raise UserError(_("This request is not waiting for the %(role)s action.", role=role))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for leave in records:
            if leave._approval_exempt():
                leave.sudo().write({'approval_state': 'done'})
            elif leave.state in ('confirm', 'validate1'):
                leave.sudo().write({'approval_state': 'submitted'})
            elif leave.state == 'validate':
                leave.sudo().write({'approval_state': 'done'})
            elif leave.state in ('refuse', 'cancel'):
                leave.sudo().write({'approval_state': 'refused'})
            else:
                leave.sudo().write({'approval_state': 'draft'})
        return records

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('leave_approval_internal'):
            return res
        if 'state' in vals:
            for leave in self:
                if leave._approval_exempt() or leave.state == 'validate':
                    target = 'done'
                elif leave.state in ('refuse', 'cancel'):
                    target = 'refused'
                elif leave.state == 'draft':
                    target = 'draft'
                elif leave.state in ('confirm', 'validate1') and leave.approval_state in ('draft', 'refused'):
                    target = 'submitted'
                else:
                    continue
                if leave.approval_state != target:
                    leave.with_context(leave_approval_internal=True).sudo().write({'approval_state': target})
        return res

    def _approval_set(self, state):
        self.with_context(leave_approval_internal=True).sudo().write({'approval_state': state})

    def _approval_close_standard(self):
        for leave in self:
            leave = leave.sudo().with_context(leave_approval_internal=True, leave_approval_closing=True)
            if leave.state == 'draft':
                leave.action_confirm()
            if leave.state in ('confirm', 'validate1'):
                # Avoid the standard approval guard below while invoking Odoo's normal validation.
                leave.with_context(leave_approval_internal=True, leave_approval_closing=True).action_validate()
            if leave.state != 'validate':
                raise UserError(_("Odoo could not validate the time off request: %s", leave.display_name))
            leave._approval_set('done')

    def action_leave_approval_manager(self):
        self.ensure_one()
        self._approval_check(('submitted',), _('manager'))
        if not self._approval_is_manager():
            raise AccessError(_("Only the employee's direct manager can approve this request."))
        self._approval_set('manager_approved')
        return True

    def action_leave_approval_hr(self):
        self._approval_check(('manager_approved',), _('HR'))
        if not self._approval_is_hr():
            raise AccessError(_('Only HR officers can process this request.'))
        self._approval_set('hr_approved')
        return True

    def action_leave_approval_hr_close(self):
        self._approval_check(('manager_approved', 'hr_approved'), _('HR close'))
        if not self._approval_is_hr():
            raise AccessError(_('Only HR officers can close this request.'))
        self._approval_close_standard()
        return True

    def action_leave_approval_send_cfo(self):
        self._approval_check(('manager_approved', 'hr_approved'), _('HR send to CFO'))
        if not self._approval_is_hr():
            raise AccessError(_('Only HR officers can send this request to the CFO.'))
        self._approval_set('cfo')
        return True

    def action_leave_approval_cfo_close(self):
        self._approval_check(('cfo',), _('CFO close'))
        if not self._approval_is_cfo():
            raise AccessError(_('Only users in the Time Off Approval - CFO group can close this request.'))
        self._approval_close_standard()
        return True

    def action_leave_approval_send_ceo(self):
        self._approval_check(('cfo',), _('CFO send to CEO'))
        if not self._approval_is_cfo():
            raise AccessError(_('Only the CFO can send this request to the CEO.'))
        self._approval_set('ceo')
        return True

    def action_leave_approval_ceo_close(self):
        self._approval_check(('ceo',), _('CEO close'))
        if not self._approval_is_ceo():
            raise AccessError(_('Only users in the Time Off Approval - CEO group can close this request.'))
        self._approval_close_standard()
        return True

    def action_leave_approval_refuse(self):
        self.ensure_one()
        if not (self._approval_is_manager() or self._approval_is_hr() or self._approval_is_cfo() or self._approval_is_ceo()):
            raise AccessError(_('You are not allowed to refuse this request.'))
        if self.state in ('confirm', 'validate1', 'validate'):
            self.sudo().with_context(leave_approval_internal=True, leave_approval_closing=True).action_refuse()
        self._approval_set('refused')
        return True

    def action_leave_approval_reset(self):
        self.ensure_one()
        if not self._approval_is_hr():
            raise AccessError(_('Only HR officers can reset this approval workflow.'))
        if self.state == 'refuse':
            if hasattr(self, 'action_reset_confirm'):
                self.sudo().action_reset_confirm()
            else:
                self.sudo().action_draft()
                self.sudo().action_confirm()
        self._approval_set('submitted')
        return True

    def action_approve(self, *args, **kwargs):
        if not self.env.context.get('leave_approval_closing') and not self.env.context.get('leave_approval_internal'):
            pending = self.filtered(lambda l: not l._approval_exempt() and l.approval_state != 'done')
            if pending:
                raise UserError(_("Use the dedicated Time Off approval workflow for these requests."))
        return super().action_approve(*args, **kwargs)

    def action_validate(self, *args, **kwargs):
        if not self.env.context.get('leave_approval_closing') and not self.env.context.get('leave_approval_internal'):
            pending = self.filtered(lambda l: not l._approval_exempt() and l.approval_state != 'done')
            if pending:
                raise UserError(_("Use the dedicated Time Off approval workflow to close these requests."))
        return super().action_validate(*args, **kwargs)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'form':
            header = arch.find('./header')
            if header is not None:
                if not arch.xpath(".//field[@name='approval_state']"):
                    header.append(etree.Element('field', {'name': 'approval_state', 'invisible': '1'}))
                # Hide standard approval controls so this workflow owns the approval path.
                for standard_name in ('action_approve', 'action_validate', 'action_refuse'):
                    for standard_button in arch.xpath(".//button[@name='%s']" % standard_name):
                        standard_button.set('invisible', 'True')
                # Add our buttons only once; do not inherit or target another module's buttons.
                buttons = [
                    ('action_leave_approval_manager', 'Manager Approve', "approval_state != 'submitted'", None),
                    ('action_leave_approval_hr', 'HR Approve', "approval_state != 'manager_approved'", 'hr_holidays.group_hr_user'),
                    ('action_leave_approval_hr_close', 'HR Approve & Close', "approval_state not in ['manager_approved', 'hr_approved']", 'hr_holidays.group_hr_user'),
                    ('action_leave_approval_send_cfo', 'Send to CFO', "approval_state not in ['manager_approved', 'hr_approved']", 'hr_holidays.group_hr_user'),
                    ('action_leave_approval_cfo_close', 'CFO Close', "approval_state != 'cfo'", 'hr_leave_approval_standalone.group_leave_approval_cfo'),
                    ('action_leave_approval_send_ceo', 'Send to CEO', "approval_state != 'cfo'", 'hr_leave_approval_standalone.group_leave_approval_cfo'),
                    ('action_leave_approval_ceo_close', 'CEO Close', "approval_state != 'ceo'", 'hr_leave_approval_standalone.group_leave_approval_ceo'),
                    ('action_leave_approval_refuse', 'Refuse Request', "approval_state in ['done', 'refused', 'draft']", None),
                    ('action_leave_approval_reset', 'Reset Approval', "approval_state != 'refused'", 'hr_holidays.group_hr_user'),
                ]
                existing = set(arch.xpath(".//button/@name"))
                for name, label, invisible, groups in buttons:
                    if name in existing:
                        continue
                    attrs = {'name': name, 'string': label, 'type': 'object', 'invisible': invisible}
                    if groups:
                        attrs['groups'] = groups
                    header.append(etree.Element('button', attrs))
                # Keep a statusbar on the form, but never depend on another workflow's view patch.
                if not arch.xpath(".//field[@name='approval_state' and @widget='statusbar']"):
                    header.append(etree.Element('field', {
                        'name': 'approval_state', 'widget': 'statusbar',
                        'statusbar_visible': 'submitted,manager_approved,hr_approved,cfo,ceo,done,refused',
                        'options': "{'clickable': False}",
                    }))
        elif view_type == 'list' and not arch.xpath(".//field[@name='approval_state']"):
            arch.append(etree.Element('field', {'name': 'approval_state', 'widget': 'badge', 'optional': 'show'}))
        return arch, view
