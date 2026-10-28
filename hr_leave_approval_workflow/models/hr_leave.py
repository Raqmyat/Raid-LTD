from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.hr_approval_workflow.models.approval_mixin import BULK
from odoo.addons.hr_approval_workflow.models.hr_payslip import _roles_groups
from odoo.addons.hr_approval_workflow.models.view_patch import approval_buttons, patch_header

from .view_patch import patch_list_column, patch_search

# Standard buttons of the old approval cycle (removed from the headers).
# Extra technical names: system parameter hr_leave_approval_workflow.hide_buttons
HIDE_NAMES = {'action_approve', 'action_validate', 'action_refuse'}
HIDE_LABELS = {'approve', 'validate', 'refuse'}


class HrLeave(models.Model):
    _name = 'hr.leave'
    _inherit = ['hr.leave', 'approval.mixin']

    # creating the request = submitting it
    approval_state = fields.Selection(default='submitted')

    # ------------------------------------------------------------------
    # views
    # ------------------------------------------------------------------
    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'search':
            patch_search(arch)
        elif view_type in ('list', 'form'):
            extra = self.env['ir.config_parameter'].sudo().get_param(
                'hr_leave_approval_workflow.hide_buttons', '')
            names = HIDE_NAMES | {n.strip() for n in extra.split(',') if n.strip()}

            def groups_for(key):
                return _roles_groups(self.env, 'hr.leave', key)

            if view_type == 'form':
                # only the full forms (with a header); never the small create dialogs
                if arch.xpath('./header'):
                    specs = approval_buttons('action_btn_', groups_for, True)
                    patch_header(arch, specs, names, HIDE_LABELS, statusbar=True)
            else:
                specs = approval_buttons('action_wizard_', groups_for, False)
                patch_header(arch, specs, names, HIDE_LABELS)
                patch_list_column(arch)
        return arch, view

    # ------------------------------------------------------------------
    # approval status follows the request
    # ------------------------------------------------------------------
    def _approval_exempt(self):
        """Leave types with 'No validation' never enter the cycle."""
        return self.filtered(lambda l: getattr(l, 'validation_type', False) == 'no_validation')

    def _approval_state_from_leave(self):
        self.ensure_one()
        if self._approval_exempt() or self.state == 'validate':
            return 'done'
        if self.state in ('refuse', 'cancel'):
            return 'refused'
        if self.state == 'draft':
            return 'draft'
        return 'submitted'

    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        silent = leaves.sudo().with_context(approval_internal=True, tracking_disable=True)
        for leave in silent:
            target = leave._approval_state_from_leave()
            if leave.approval_state != target:
                leave.write({'approval_state': target})
        leaves.filtered(lambda l: l.approval_state == 'submitted')._approval_notify()
        return leaves

    def write(self, vals):
        res = super().write(vals)
        new_state = vals.get('state')
        if new_state:
            silent = bool(self.env.context.get('approval_closing'))
            if new_state in ('refuse', 'cancel'):
                todo = self.filtered(lambda l: l.approval_state not in ('done', 'refused'))
                target = 'refused'
            elif new_state == 'draft':
                todo = self.filtered(lambda l: l.approval_state != 'draft')
                target = 'draft'
            elif new_state == 'confirm':
                todo = self.filtered(lambda l: l.approval_state in ('draft', 'refused'))
                target = 'submitted'
            else:
                todo, target = self.browse(), None
            if todo:
                todo.with_context(approval_no_notify=silent)._approval_set(target)
        return res

    def _approval_initial_state(self):
        return 'submitted'

    # ------------------------------------------------------------------
    # wizard / notification details
    # ------------------------------------------------------------------
    def _approval_wizard_line_vals(self):
        vals = super()._approval_wizard_line_vals()
        d_from = fields.Date.to_date(self.date_from)
        d_to = fields.Date.to_date(self.date_to)
        vals.update({
            'name': self.employee_id.name or self.display_name,
            'extra': '%s  |  %s → %s  |  %g day(s)' % (
                self.holiday_status_id.name or '', d_from or '', d_to or '',
                self.number_of_days or 0.0),
        })
        return vals

    def _approval_notify_name(self):
        return '%s (%s)' % (self.employee_id.name or self.display_name,
                            self.holiday_status_id.name or '')

    def _approval_notify_targets(self):
        # one message for the whole set, posted on the first request
        return [(self[0], self)] if self else []

    @api.model
    def _approval_menu_action(self, key):
        """Menu entry without any selection: all requests waiting for this button."""
        leaves = self.search([('approval_state', 'in', list(BULK[key]))])
        return leaves._approval_open_wizard(key)

    # ------------------------------------------------------------------
    # closing / refusing / resetting drive the standard request
    # ------------------------------------------------------------------
    def _approval_on_done(self):
        for leave in self.filtered(lambda l: l.state in ('draft', 'confirm', 'validate1')):
            leave = leave.sudo().with_context(approval_closing=True)
            if leave.state == 'draft':
                leave.action_confirm()
            leave.action_validate()

    def _approval_on_refused(self):
        to_refuse = self.filtered(lambda l: l.state in ('confirm', 'validate1', 'validate'))
        if to_refuse:
            to_refuse.sudo().with_context(approval_closing=True).action_refuse()

    def _approval_on_reset(self):
        for leave in self.filtered(lambda l: l.state == 'refuse').sudo():
            if hasattr(leave, 'action_reset_confirm'):
                leave.action_reset_confirm()
            else:
                if hasattr(leave, 'action_draft'):
                    leave.action_draft()
                if hasattr(leave, 'action_confirm'):
                    leave.action_confirm()
            if leave.state not in ('draft', 'confirm'):
                raise UserError(_(
                    "%s could not be reset to 'To Approve'. Reset it from the standard "
                    "Time Off screen first.", leave.display_name))

    # ------------------------------------------------------------------
    # block the standard approval until the cycle is finished
    # ------------------------------------------------------------------
    def _approval_enforce_check(self):
        if self.env.context.get('approval_closing'):
            return
        enforce = self.env['ir.config_parameter'].sudo().get_param(
            'hr_leave_approval_workflow.enforce', 'True')
        if enforce in ('False', '0'):
            return
        pending = (self - self._approval_exempt()).filtered(lambda l: l.approval_state != 'done')
        if pending:
            raise UserError(_(
                "These time off requests must go through the approval workflow:\n%s",
                '\n'.join(pending.mapped('display_name'))))

    def action_approve(self, *args, **kwargs):
        self._approval_enforce_check()
        return super().action_approve(*args, **kwargs)

    def action_validate(self, *args, **kwargs):
        self._approval_enforce_check()
        return super().action_validate(*args, **kwargs)
