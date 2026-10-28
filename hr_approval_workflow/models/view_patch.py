from lxml import etree

from .approval_mixin import BULK, BUTTONS

STATUSBAR_VISIBLE = 'draft,submitted,ops_approved,hr_approved,finance,ceo,done'


def approval_buttons(prefix, group_xmlids_for, with_state_visibility):
    """Button specs for the headers.
    prefix: method prefix (action_btn_ / action_wizard_ / action_run_)
    group_xmlids_for(key) -> list of group xmlids allowed to see the button."""
    specs = []
    for key, label, css in BUTTONS:
        invisible = None
        if with_state_visibility:
            invisible = "approval_state not in %s" % list(BULK[key])
        specs.append({
            'name': '%s%s' % (prefix, key), 'string': label, 'class': css,
            'groups': ','.join(group_xmlids_for(key)), 'invisible': invisible,
        })
    return specs


def patch_header(arch, specs, hide_names=(), hide_labels=(), statusbar=False):
    """Works on any header structure: removes the old buttons, puts the
    approval buttons FIRST (same row as the standard ones) and optionally
    the approval status bar at the end of the header."""
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
    if statusbar and not arch.xpath("//header/field[@name='approval_state']"):
        header.append(etree.Element('field', {
            'name': 'approval_state', 'widget': 'statusbar', 'readonly': '1',
            'statusbar_visible': STATUSBAR_VISIBLE,
        }))
    return arch
