from lxml import etree

from .approval_mixin import BULK, BUTTONS


def approval_buttons(prefix, group_xmlids_for, with_state_visibility):
    """Button specs for the headers.
    prefix: method prefix (action_btn_ / action_wizard_ / action_run_)
    group_xmlids_for(key, state=None) -> list of group xmlids allowed to see the button.
    with_state_visibility: one button per (action, status), shown only in that status
    and only to the role that acts on it (so e.g. Operations no longer sees
    "Approve" again once the payslip is Operations Approved)."""
    specs = []
    for key, label, css in BUTTONS:
        if with_state_visibility:
            for state in BULK[key]:
                specs.append({
                    'name': '%s%s__%s' % (prefix, key, state), 'string': label, 'class': css,
                    'groups': ','.join(group_xmlids_for(key, state)),
                    'invisible': "state != '%s'" % state,
                })
        else:
            specs.append({
                'name': '%s%s' % (prefix, key), 'string': label, 'class': css,
                'groups': ','.join(group_xmlids_for(key)), 'invisible': None,
            })
    return specs


def patch_header(arch, specs, hide_names=(), hide_labels=(), statusbar_visible=None):
    """Works on any header structure: removes the old buttons, puts the
    approval buttons FIRST (same row as the standard ones) and optionally
    widens the statusbar of the standard `state` field (statusbar_visible)."""
    for btn in arch.xpath('//header//button'):
        label = (btn.get('string') or '').strip().lower()
        if btn.get('name') in hide_names or label in hide_labels:
            btn.getparent().remove(btn)
    headers = arch.xpath('./header')
    if headers:
        header = headers[0]
    else:
        header = etree.Element('header')
        arch.insert(0, header)
    idx = 0
    for spec in specs:
        if arch.xpath("//button[@name='%s']" % spec['name']):
            continue  # already patched
        attrs = {'name': spec['name'], 'type': 'object', 'string': spec['string'],
                 'class': spec['class'], 'groups': spec['groups']}
        if spec.get('invisible'):
            attrs['invisible'] = spec['invisible']
        header.insert(idx, etree.Element('button', attrs))
        idx += 1
    if statusbar_visible:
        for field in arch.xpath("//header/field[@name='state']"):
            field.set('statusbar_visible', statusbar_visible)
    return arch
