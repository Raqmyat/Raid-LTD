from lxml import etree

from odoo.addons.hr_approval_workflow.models.approval_mixin import APPROVAL_STATES


def patch_list_column(arch):
    """Append the approval status column to a list view."""
    if arch.tag != 'list' or arch.xpath(".//field[@name='approval_state']"):
        return arch
    arch.append(etree.Element('field', {
        'name': 'approval_state', 'widget': 'badge', 'optional': 'show',
        'decoration-muted': "approval_state == 'draft'",
        'decoration-info': "approval_state in ('submitted', 'ops_approved', 'hr_approved')",
        'decoration-warning': "approval_state in ('finance', 'ceo')",
        'decoration-success': "approval_state == 'done'",
        'decoration-danger': "approval_state == 'refused'",
    }))
    return arch


def patch_search(arch):
    """Approval filters + group by in the search view."""
    search = arch if arch.tag == 'search' else arch.find('.//search')
    if search is None or search.xpath(".//filter[@name='approval_my_turn']"):
        return arch
    search.append(etree.Element('separator'))
    search.append(etree.Element('field', {'name': 'approval_state'}))
    search.append(etree.Element('filter', {
        'name': 'approval_my_turn', 'string': 'Approval: My Turn',
        'domain': "[('approval_my_turn', '=', True)]"}))
    for code, label in APPROVAL_STATES:
        search.append(etree.Element('filter', {
            'name': 'approval_f_%s' % code, 'string': 'Approval: %s' % label,
            'domain': "[('approval_state', '=', '%s')]" % code}))
    group = etree.SubElement(search, 'group', {'expand': '0', 'string': 'Approval'})
    etree.SubElement(group, 'filter', {
        'name': 'approval_group_by', 'string': 'Approval Status',
        'context': "{'group_by': 'approval_state'}"})
    return arch
