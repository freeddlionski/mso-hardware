"""Чтение нетлиста KiCad (формат kicadsexpr, выгрузка CI в ветку kicad-out: mso74-plata.net)."""
from sexp import parse


def _kids(node, tag):
    return [x for x in node if isinstance(x, list) and x and x[0] == tag]


def _val(node, tag, default=''):
    k = _kids(node, tag)
    return str(k[0][1]) if k and len(k[0]) > 1 else default


class Comp:
    def __init__(self, ref, value, fp, sheet, props):
        self.ref, self.value, self.fp, self.sheet, self.props = ref, value, fp, sheet, props
        self.dnp = 'dnp' in props or props.get('DNP') == 'DNP'
        self.pins = {}          # номер вывода → имя цепи

    def __repr__(self):
        return '%s %s %s' % (self.ref, self.value, self.fp)


def read(path):
    """Вернуть (comps: dict ref→Comp, nets: dict имя→[(ref, pin)])."""
    root = parse(open(path, encoding='utf-8').read())
    if root and isinstance(root[0], list):
        root = root[0]
    comps = {}
    for c in _kids(_kids(root, 'components')[0], 'comp'):
        props = {}
        for p in _kids(c, 'property'):
            name = _val(p, 'name')
            props[name] = _val(p, 'value')
        sheet, sheet_ts = '', '/'
        sp = _kids(c, 'sheetpath')
        if sp:
            sheet, sheet_ts = _val(sp[0], 'names'), _val(sp[0], 'tstamps', '/')
        comp = Comp(_val(c, 'ref'), _val(c, 'value'), _val(c, 'footprint'), sheet, props)
        comp.path = sheet_ts + _val(c, 'tstamps')          # связь платы со схемой (KIID_PATH)
        comps[comp.ref] = comp
    nets = {}
    for n in _kids(_kids(root, 'nets')[0], 'net'):
        name = _val(n, 'name')
        nodes = [(_val(x, 'ref'), _val(x, 'pin')) for x in _kids(n, 'node')]
        nets[name] = nodes
        for ref, pin in nodes:
            if ref in comps:
                comps[ref].pins[pin] = name
    return comps, nets
