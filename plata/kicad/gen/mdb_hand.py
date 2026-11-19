"""Ручная доводка меди MDB после Freerouting, по тексту файла платы.

18.11.2026 (применено, медь потом переразведена проходом 15 — списки сняты, история в git):
- MDB_TX_E отведена от площадки +24 В F3; переход +24V_P F3.1 перенесён в площадку; +5V к Q12.2 / U24.1.
19.11.2026, проход 15:
- поля LCSC/MPN деталей правки берутся из схемы io.kicad_sch (pcbnew в pcb_mdb.py пишет их мимо — без них детали
  выпадают из BOM заводу);
- REMOVE / ADD — доводка после трассировки прохода 15 (если понадобится по DRC).

Повторный запуск ничего не меняет (снимаем только найденное, добавляем только отсутствующее).
Запуск: python3 mdb_hand.py ../routed/mso74-plata.kicad_pcb
"""
import sys
import uuid
from pathlib import Path

from eco_text import Board
from sexp import Q, find, findall, parse

NEW = ('Q10', 'Q11', 'Q12', 'R119', 'R120', 'R121', 'R122', 'U24', 'D17', 'D21', 'R64', 'F6', 'F7', 'D50')
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
    # проход 15: обрезок 0,14 мм от прежней дорожки +5V к U24.1 (DRC track_dangling)
    ('seg', P5, (157.916, 127.232), (157.814, 127.334)),
]

ADD = []


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
