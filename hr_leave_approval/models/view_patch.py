from lxml import etree

STATUSBAR_VISIBLE = 'draft,manager,hr,cfo,ceo,done'
STATES = [('draft', 'To Submit'), ('manager', 'Waiting Manager'), ('hr', 'Waiting HR'),
          ('cfo', 'Waiting CFO'), ('ceo', 'Waiting CEO'), ('done', 'Approved'),
          ('refused', 'Refused')]


def patch_header(arch, specs, hide_names=(), hide_labels=(), statusbar=False,
                 create_header=True):
    """Removes the old buttons, puts the approval buttons FIRST in the header
    (same row as the standard ones) and optionally the approval status bar last."""
    for btn in arch.xpath('//header//button'):
        label = (btn.get('string') or '').strip().lower()
        if btn.get('name') in hide_names or label in hide_labels:
            btn.getparent().remove(btn)
    headers = arch.xpath('./header')
    if headers:
        header = headers[0]
    elif create_header:
        header = etree.Element('header')
        arch.insert(0, header)
    else:
        return arch
    idx = 0
    for spec in specs:
        if arch.xpath("//button[@name='%s']" % spec['name']):
            continue
        attrs = {'name': spec['name'], 'type': 'object', 'string': spec['string'],
                 'class': spec['class']}
        for opt in ('groups', 'invisible'):
            if spec.get(opt):
                attrs[opt] = spec[opt]
        header.insert(idx, etree.Element('button', attrs))
        idx += 1
    if statusbar:
        if not arch.xpath("//header/field[@name='leave_approval_state']"):
            header.append(etree.Element('field', {
                'name': 'leave_approval_state', 'widget': 'statusbar', 'readonly': '1',
                'statusbar_visible': STATUSBAR_VISIBLE}))
        if not arch.xpath("//field[@name='leave_can_act']"):
            arch.append(etree.Element('field', {'name': 'leave_can_act', 'invisible': '1'}))
    return arch


def patch_list_column(arch):
    if arch.tag != 'list' or arch.xpath(".//field[@name='leave_approval_state']"):
        return arch
    arch.append(etree.Element('field', {
        'name': 'leave_approval_state', 'widget': 'badge', 'optional': 'show',
        'decoration-muted': "leave_approval_state == 'draft'",
        'decoration-info': "leave_approval_state in ('manager', 'hr')",
        'decoration-warning': "leave_approval_state in ('cfo', 'ceo')",
        'decoration-success': "leave_approval_state == 'done'",
        'decoration-danger': "leave_approval_state == 'refused'",
    }))
    return arch


def patch_search(arch):
    search = arch if arch.tag == 'search' else arch.find('.//search')
    if search is None or search.xpath(".//filter[@name='lv_my_turn']"):
        return arch
    search.append(etree.Element('separator'))
    search.append(etree.Element('field', {'name': 'leave_approval_state'}))
    search.append(etree.Element('filter', {
        'name': 'lv_my_turn', 'string': 'Approval: My Turn',
        'domain': "[('leave_approval_my_turn', '=', True)]"}))
    for code, label in STATES:
        search.append(etree.Element('filter', {
            'name': 'lv_f_%s' % code, 'string': 'Approval: %s' % label,
            'domain': "[('leave_approval_state', '=', '%s')]" % code}))
    group = etree.SubElement(search, 'group', {'expand': '0', 'string': 'Approval'})
    etree.SubElement(group, 'filter', {
        'name': 'lv_group_by', 'string': 'Approval Status',
        'context': "{'group_by': 'leave_approval_state'}"})
    return arch
