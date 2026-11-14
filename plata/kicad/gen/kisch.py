"""Генератор схем KiCad 9 из официальных символов.

Схема строится «выводами с метками»: у каждого вывода короткий проводник и метка цепи (или символ питания).
Так схему легко генерировать и проверять: ERC в CI ловит любой неподключённый вывод и висящую метку.
Каждый вывод детали обязан получить цепь или явную отметку «не подключён» — иначе генератор падает.
"""
import copy
import math
import os
import uuid as _uuid

from sexp import Q, parse, dump, find, findall

GRID = 1.27
STUB = 2.54
PROJECT = 'mso74-plata'
VERSION = '20250114'

_lib_cache = {}


def _uid(*parts):
    # детерминированные UUID — повторная генерация не меняет файл без причины
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, 'mso74/' + '/'.join(str(p) for p in parts)))


def _snap(v):
    return round(round(v / GRID) * GRID, 4)


class Lib:
    def __init__(self, dirs):
        self.dirs = dirs

    def _file(self, lib):
        for d in self.dirs:
            p = os.path.join(d, lib + '.kicad_sym')
            if os.path.exists(p):
                return p
        raise FileNotFoundError(lib)

    def _top(self, lib):
        if lib not in _lib_cache:
            tree = parse(open(self._file(lib), encoding='utf-8').read())
            _lib_cache[lib] = {s[1]: s for s in findall(tree, 'symbol')}
        return _lib_cache[lib]

    def symbol(self, lib_id):
        lib, name = lib_id.split(':')
        sym = copy.deepcopy(self._top(lib)[name])
        ext = find(sym, 'extends')
        if ext:
            parent = self.symbol(lib + ':' + ext[1])
            props = {p[1]: p for p in findall(sym, 'property')}
            out = [x for x in parent if not (isinstance(x, list) and x[0] == 'property')]
            pname = parent[1].split(':')[-1]
            for p in findall(parent, 'property'):
                out.append(props.pop(p[1], p))
            out.extend(props.values())
            for sub in findall(out, 'symbol'):
                sub[1] = Q(sub[1].replace(pname + '_', name + '_', 1))
            sym = out
        sym[1] = Q(lib_id)
        return sym


def pins_of(sym, unit):
    name = sym[1].split(':')[-1]
    res = []
    for sub in findall(sym, 'symbol'):
        u, s = sub[1][len(name) + 1:].split('_')
        if int(u) not in (0, unit) or int(s) not in (0, 1):
            continue
        for p in findall(sub, 'pin'):
            at = find(p, 'at')
            res.append(dict(type=p[1], name=str(find(p, 'name')[1]), number=str(find(p, 'number')[1]),
                            x=float(at[1]), y=float(at[2]), a=int(float(at[3])) % 360,
                            hidden=any(x == 'hide' or (isinstance(x, list) and x[:2] == ['hide', 'yes']) for x in p)))
    return res


def units_of(sym):
    name = sym[1].split(':')[-1]
    us = set()
    for sub in findall(sym, 'symbol'):
        us.add(int(sub[1][len(name) + 1:].split('_')[0]))
    us.discard(0)
    return sorted(us) or [1]


def _rot(x, y, r):
    c, s = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    return x * c - y * s, x * s + y * c


DIRS = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}   # угол вывода в библиотеке → наружу (в координатах листа)
LABEL_ANGLE = {(-1, 0): 180, (1, 0): 0, (0, -1): 90, (0, 1): 270}


class Part:
    def __init__(self, sheet, lib_id, ref, value, at, unit=1, rot=0, fp='', lcsc='', mpn='', fields=None, dnp=False):
        self.sheet, self.lib_id, self.ref, self.value = sheet, lib_id, ref, value
        self.at, self.unit, self.rot = (_snap(at[0]), _snap(at[1])), unit, rot
        self.fp, self.lcsc, self.mpn, self.fields, self.dnp = fp, lcsc, mpn, fields or {}, dnp
        self.sym = sheet.proj.lib.symbol(lib_id)
        self.pins = pins_of(self.sym, unit)
        self.nets = {}

    def pin(self, key):
        found = [p for p in self.pins if p['number'] == key] or [p for p in self.pins if p['name'] == key]
        if not found:
            raise KeyError('%s (%s): нет вывода %s; есть %s' % (self.ref, self.lib_id, key,
                           [(p['number'], p['name']) for p in self.pins]))
        return found

    def pos(self, p):
        x, y = _rot(p['x'], p['y'], self.rot)
        return _snap(self.at[0] + x), _snap(self.at[1] - y)

    def outward(self, p):
        a = (p['a'] + self.rot) % 360
        return DIRS[a]


class Sheet:
    def __init__(self, proj, name, title, paper='A3'):
        self.proj, self.name, self.title, self.paper = proj, name, title, paper
        self.parts, self.items, self.texts = [], [], []
        self.uuid = _uid('sheet', name)
        proj.sheets.append(self)

    def part(self, lib_id, prefix, value, at, **kw):
        ref = kw.pop('ref', None) or self.proj.next_ref(prefix)
        p = Part(self, lib_id, ref, value, at, **kw)
        self.parts.append(p)
        return p

    def connect(self, part, mapping, nc=()):
        for key, net in mapping.items():
            for p in part.pin(key):
                part.nets[p['number']] = net
        for key in nc:
            for p in part.pin(key):
                part.nets[p['number']] = None

    def text(self, s, at, size=1.27):
        self.texts.append((s, at, size))


class Project:
    def __init__(self, lib_dirs, power_nets):
        self.lib = Lib(lib_dirs)
        self.sheets = []
        self.power = set(power_nets)
        self._refs = {}
        self.root_uuid = _uid('root')

    def next_ref(self, prefix):
        n = self._refs.get(prefix, 0) + 1
        self._refs[prefix] = n
        return '%s%d' % (prefix, n)

    # ---- запись ----
    def _net_sheets(self):
        where = {}
        for sh in self.sheets:
            for part in sh.parts:
                for net in part.nets.values():
                    if net:
                        where.setdefault(net, set()).add(sh.name)
        return where

    def check(self):
        for sh in self.sheets:
            for part in sh.parts:
                missing = [(p['number'], p['name']) for p in part.pins if p['number'] not in part.nets]
                if missing:
                    raise ValueError('%s %s: не назначены выводы %s' % (part.ref, part.lib_id, missing))
        # цепь из одного вывода — почти всегда ошибка
        cnt = {}
        for sh in self.sheets:
            for part in sh.parts:
                for num, net in part.nets.items():
                    if net:
                        cnt.setdefault(net, []).append('%s.%s' % (part.ref, num))
        lonely = {n: v for n, v in cnt.items() if len(v) < 2}
        if lonely:
            raise ValueError('цепи с одним выводом: %s' % lonely)
        return cnt

    def write(self, outdir):
        self.check()
        where = self._net_sheets()
        used_syms = {}
        for sh in self.sheets:
            for part in sh.parts:
                used_syms.setdefault(part.lib_id, part.sym)
        for i, sh in enumerate(self.sheets):
            self._write_sheet(sh, outdir, where, page=i + 2)
        self._write_root(outdir)
        return used_syms

    def _props(self, part, uid_base):
        out = []
        base = {p[1]: p for p in findall(part.sym, 'property')}

        def prop(name, val, hide, dx=None, dy=None):
            src = base.get(name)
            if src is not None and find(src, 'at'):
                at = find(src, 'at')
                x, y = _rot(float(at[1]), float(at[2]), part.rot)
            else:
                x, y = 0.0, 0.0
            eff = ['effects', ['font', ['size', 1.27, 1.27]]]
            if src is not None and find(src, 'effects') and find(find(src, 'effects'), 'justify'):
                eff.append(copy.deepcopy(find(find(src, 'effects'), 'justify')))
            if hide:
                eff.append(['hide', 'yes'])
            return ['property', Q(name), Q(val), ['at', _snap(part.at[0] + x), _snap(part.at[1] - y), 0], eff]

        out.append(prop('Reference', part.ref, False))
        out.append(prop('Value', part.value, False))
        out.append(prop('Footprint', part.fp or (str(base['Footprint'][2]) if 'Footprint' in base else ''), True))
        out.append(prop('Datasheet', str(base['Datasheet'][2]) if 'Datasheet' in base else '', True))
        out.append(prop('LCSC', part.lcsc, True))
        if part.mpn:
            out.append(prop('MPN', part.mpn, True))
        for k, v in part.fields.items():
            out.append(prop(k, v, True))
        return out

    def _write_sheet(self, sh, outdir, where, page):
        items = []
        path = '/%s/%s' % (self.root_uuid, sh.uuid)
        for part in sh.parts:
            uid = _uid(sh.name, part.ref, part.unit)
            sym = ['symbol', ['lib_id', Q(part.lib_id)], ['at', part.at[0], part.at[1], part.rot], ['unit', part.unit],
                   ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'], ['dnp', 'yes' if part.dnp else 'no'],
                   ['uuid', Q(uid)]]
            sym += self._props(part, uid)
            for num in sorted({p['number'] for p in part.pins}, key=lambda s: (len(s), s)):
                sym.append(['pin', Q(num), ['uuid', Q(_uid(uid, 'pin', num))]])
            sym.append(['instances', ['project', Q(PROJECT), ['path', Q(path), ['reference', Q(part.ref)], ['unit', part.unit]]]])
            items.append(sym)
            for p in part.pins:
                net = part.nets[p['number']]
                x, y = part.pos(p)
                key = (part.ref, part.unit, p['number'])
                if net is None:
                    items.append(['no_connect', ['at', x, y], ['uuid', Q(_uid(sh.name, 'nc', *key))]])
                    continue
                dx, dy = part.outward(p)
                ex, ey = _snap(x + dx * STUB), _snap(y + dy * STUB)
                items.append(['wire', ['pts', ['xy', x, y], ['xy', ex, ey]], ['stroke', ['width', 0], ['type', 'default']],
                              ['uuid', Q(_uid(sh.name, 'w', *key))]])
                items.append(self._net_item(sh, net, ex, ey, (dx, dy), where, key))
        for s, at, size in sh.texts:
            items.append(['text', Q(s), ['exclude_from_sim', 'no'], ['at', _snap(at[0]), _snap(at[1]), 0],
                          ['effects', ['font', ['size', size, size]], ['justify', 'left', 'bottom']],
                          ['uuid', Q(_uid(sh.name, 'text', s[:40], at))]])
        self._emit(os.path.join(outdir, sh.name + '.kicad_sch'), sh.uuid, sh.paper, sh.title, page, items, root=False)

    def _net_item(self, sh, net, x, y, d, where, key):
        uid = Q(_uid(sh.name, 'n', *key))
        if net in self.power:
            lib_id = 'power:GND' if net == 'GND' else 'power:+5V'
            # корпус символа питания — по направлению вывода наружу
            if net == 'GND':
                rot = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}[d]
            else:
                rot = {(0, -1): 0, (-1, 0): 90, (0, 1): 180, (1, 0): 270}[d]
            sym = self.lib.symbol(lib_id)
            self._power_syms[lib_id] = sym
            ref = '#PWR%04d' % self._pwr_next()
            vx, vy = _rot(0, 3.81 if net != 'GND' else -3.81, rot)
            return ['symbol', ['lib_id', Q(lib_id)], ['at', x, y, rot], ['unit', 1], ['exclude_from_sim', 'no'],
                    ['in_bom', 'yes'], ['on_board', 'yes'], ['dnp', 'no'], ['uuid', uid],
                    ['property', Q('Reference'), Q(ref), ['at', x, y, 0], ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]],
                    ['property', Q('Value'), Q(net), ['at', _snap(x + vx), _snap(y - vy), 0], ['effects', ['font', ['size', 1.27, 1.27]]]],
                    ['property', Q('Footprint'), Q(''), ['at', x, y, 0], ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]],
                    ['property', Q('Datasheet'), Q(''), ['at', x, y, 0], ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]],
                    ['pin', Q('1'), ['uuid', Q(_uid(uid, 'p1'))]],
                    ['instances', ['project', Q(PROJECT), ['path', Q('/%s/%s' % (self.root_uuid, sh.uuid)), ['reference', Q(ref)], ['unit', 1]]]]]
        ang = LABEL_ANGLE[d]
        just = ['justify', 'right' if ang == 180 else 'left', 'bottom'] if ang in (0, 180) else ['justify', 'left', 'bottom']
        if ang in (90, 270):
            just = ['justify', 'right' if ang == 270 else 'left', 'bottom']
        if len(where.get(net, ())) > 1:
            return ['global_label', Q(net), ['shape', 'bidirectional'], ['at', x, y, ang], ['fields_autoplaced', 'yes'],
                    ['effects', ['font', ['size', 1.27, 1.27]], [just[0], just[1]]], ['uuid', uid],
                    ['property', Q('Intersheetrefs'), Q('${INTERSHEET_REFS}'), ['at', x, y, 0],
                     ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]]]
        return ['label', Q(net), ['at', x, y, ang], ['effects', ['font', ['size', 1.27, 1.27]], just], ['uuid', uid]]

    _pwr = 0
    _power_syms = {}

    def _pwr_next(self):
        Project._pwr += 1
        return Project._pwr

    def _emit(self, path, uid, paper, title, page, items, root):
        libsyms = {}
        if not root:
            for it in items:
                if it[0] == 'symbol':
                    lid = str(find(it, 'lib_id')[1])
                    if lid not in libsyms:
                        libsyms[lid] = self._power_syms.get(lid) or next(
                            p.sym for sh in self.sheets for p in sh.parts if p.lib_id == lid)
        head = ['kicad_sch', ['version', VERSION], ['generator', Q('eeschema')], ['generator_version', Q('9.0')],
                ['uuid', Q(uid)], ['paper', Q(paper)],
                ['title_block', ['title', Q(title)], ['date', Q('2026-11-14')], ['rev', Q('A')],
                 ['company', Q('МСО74 · mso74.ru · Кольман Павел')], ['comment', 1, Q('Сгенерировано plata/kicad/gen — правки в генераторе, не в файле')]],
                ['lib_symbols'] + [libsyms[k] for k in sorted(libsyms)]]
        tail = [['sheet_instances', ['path', Q('/'), ['page', Q('1')]]]] if root else []
        tail.append(['embedded_fonts', 'no'])
        doc = head + items + tail
        with open(path, 'w', encoding='utf-8') as f:
            f.write(dump(doc) + '\n')

    def _write_root(self, outdir):
        items = []
        for i, sh in enumerate(self.sheets):
            x, y = 25.4 + (i % 4) * 63.5, 30.48 + (i // 4) * 38.1
            items.append(['sheet', ['at', x, y], ['size', 50.8, 25.4], ['exclude_from_sim', 'no'], ['in_bom', 'yes'],
                          ['on_board', 'yes'], ['dnp', 'no'], ['fields_autoplaced', 'yes'],
                          ['stroke', ['width', 0.1524], ['type', 'solid']], ['fill', ['color', 0, 0, 0, 0.0]],
                          ['uuid', Q(sh.uuid)],
                          ['property', Q('Sheetname'), Q(sh.title), ['at', x, _snap(y - 0.7), 0],
                           ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'bottom']]],
                          ['property', Q('Sheetfile'), Q(sh.name + '.kicad_sch'), ['at', x, _snap(y + 26.0), 0],
                           ['effects', ['font', ['size', 1.27, 1.27]], ['justify', 'left', 'top'], ['hide', 'yes']]],
                          ['instances', ['project', Q(PROJECT), ['path', Q('/' + self.root_uuid), ['page', Q(str(i + 2))]]]]])
        self._emit(os.path.join(outdir, PROJECT + '.kicad_sch'), self.root_uuid, 'A4',
                   'Плата контроллера МСО74 — ревизия A', 1, items, root=True)
