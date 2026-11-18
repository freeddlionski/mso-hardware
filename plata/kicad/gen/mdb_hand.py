"""Ручная доводка меди MDB после Freerouting (2026-11-18), по тексту файла платы.

- MDB_TX_E: дорожка R122.2 → Q12.1 шла в 0,28 мм от площадки +24 В предохранителя F3 — убрана; новая: R122.2 →
  переход → B.Cu вниз → переход между Q12.1 и Q12.2.
- +24V_P: переход F3.1 → B.Cu перенесён в площадку F3.1 (на линию B.Cu 157,62) — освобождает проход для +5V.
- +5V: Q12.2 / U24.1 были островом — R121.1 → переход → B.Cu вдоль F3 → переход у Q12.2.
- висящий переход +5V (157,81; 127,33) — убран (обе дорожки на F.Cu).
- поля LCSC/MPN новых деталей были пустые (pcbnew в pcb_mdb.py записал их мимо) — без них детали выпадали из BOM
  заводу; берутся из схемы io.kicad_sch.

Повторный запуск ничего не меняет (снимаем только найденное, добавляем только отсутствующее).
Запуск: python3 mdb_hand.py ../routed/mso74-plata.kicad_pcb
"""
import sys
import uuid
from pathlib import Path

from eco_text import Board
from sexp import Q, find, findall, parse

NEW = ('Q10', 'Q11', 'Q12', 'R119', 'R120', 'R121', 'R122', 'U24')
SCH = Path(__file__).resolve().parent.parent / 'io.kicad_sch'


def sch_fields():
    out = {}
    tree = parse(SCH.read_text(encoding='utf-8'))
    for sym in findall(tree, 'symbol'):
        props = {str(p[1]): str(p[2]) for p in findall(sym, 'property')}
        if props.get('Reference') in NEW:
            out[props['Reference']] = {k: props.get(k, '') for k in ('LCSC', 'MPN')}
    return out


def fix_fields(b):
    want = sch_fields()
    n = 0
    for fp in b.footprints():
        r = b.ref(fp)
        if r not in want:
            continue
        for p in findall(fp, 'property'):
            k = str(p[1])
            if k in want[r] and want[r][k] and str(p[2]) != want[r][k]:
                p[2] = Q(want[r][k])
                n += 1
    missing = set(NEW) - set(want)
    if missing:
        raise SystemExit('нет в схеме: %s' % sorted(missing))
    return n

E, P5, P24 = '/MDB и входы/MDB_TX_E', '+5V', '+24V_P'

REMOVE = [
    ('seg', E, (154.41, 118.5), (155.99, 120.08)),
    ('seg', E, (155.99, 120.08), (155.99, 121.55)),
    ('seg', E, (155.99, 121.55), (156.36, 121.92)),
    ('seg', E, (156.36, 121.92), (156.36, 123.58)),
    ('seg', E, (156.36, 123.58), (155.25, 124.69)),
    ('via', P24, (156.02, 118.6)),
    ('seg', P24, (157.34, 118.6), (156.02, 118.6)),
    ('seg', P24, (156.02, 118.6), (157.62, 118.6)),
    ('via', P5, (157.81, 127.33)),
]

ADD = [
    # MDB_TX_E
    ('seg', E, 'F.Cu', 0.25, (154.41, 118.5), (155.3, 119.4)),
    ('via', E, (155.3, 119.4)),
    ('seg', E, 'B.Cu', 0.25, (155.3, 119.4), (155.8, 119.9)),
    ('seg', E, 'B.Cu', 0.25, (155.8, 119.9), (155.8, 124.69)),
    ('via', E, (155.8, 124.69)),
    ('seg', E, 'F.Cu', 0.25, (155.25, 124.69), (155.8, 124.69)),
    # +24V_P
    ('via', P24, (157.62, 118.6)),
    # +5V
    ('seg', P5, 'F.Cu', 0.3, (152.18, 116.75), (152.2, 115.5)),
    ('via', P5, (152.2, 115.5)),
    ('seg', P5, 'B.Cu', 0.3, (152.2, 115.5), (156.45, 115.5)),
    ('seg', P5, 'B.Cu', 0.3, (156.45, 115.5), (156.45, 123.0)),
    ('seg', P5, 'B.Cu', 0.3, (156.45, 123.0), (157.2, 123.4)),
    ('via', P5, (157.2, 123.4)),
    ('seg', P5, 'F.Cu', 0.3, (157.2, 123.4), (156.7, 123.95)),
]


def near(a, b, r=0.02):
    return abs(a[0] - b[0]) <= r and abs(a[1] - b[1]) <= r


def match(b, node, spec):
    k, pts, hw, L, net = b.tinfo(node)
    if k != spec[0] or net != spec[1]:
        return False
    if k == 'via':
        return near(pts[0], spec[2])
    return (near(pts[0], spec[2]) and near(pts[1], spec[3])) or (near(pts[0], spec[3]) and near(pts[1], spec[2]))


def node_text(b, spec):
    no = b.net_no[spec[1]]
    u = str(uuid.uuid4())
    if spec[0] == 'via':
        x, y = spec[2]
        return ('(via (at %g %g) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net %s) (uuid "%s"))'
                % (x, y, no, u))
    _, _, L, w, (x1, y1), (x2, y2) = spec
    return ('(segment (start %g %g) (end %g %g) (width %g) (layer "%s") (net %s) (uuid "%s"))'
            % (x1, y1, x2, y2, w, L, no, u))


def main(path):
    b = Board(path)
    removed = 0
    for spec in REMOVE:
        hits = [n for n in b.tracks() if match(b, n, spec)]
        for n in hits:
            b.tree.remove(n)
            removed += 1
        if not hits:
            print('нет (уже снято?):', spec)
    added = 0
    for spec in ADD:
        if spec[0] == 'via':
            probe = spec
        else:
            probe = ('seg', spec[1], spec[4], spec[5])
        if any(match(b, n, probe) for n in b.tracks()):
            continue
        node = parse(node_text(b, spec))
        idx = max(i for i, n in enumerate(b.tree) if isinstance(n, list) and n and n[0] in ('segment', 'via'))
        b.tree.insert(idx + 1, node)
        added += 1
    fields = fix_fields(b)
    b.save()
    print('снято %d, добавлено %d, полей LCSC/MPN %d' % (removed, added, fields))


def fill(path):
    """Перезалить зоны (только в контейнере KiCad)."""
    import pcbnew
    import pcb_route
    board = pcb_route.load(path)
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcb_route.save(board, path)


if __name__ == '__main__':
    if sys.argv[1] == 'fill':
        fill(sys.argv[2])
    else:
        main(sys.argv[1])
