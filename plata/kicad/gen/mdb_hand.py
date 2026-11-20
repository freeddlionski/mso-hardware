"""Ручная доводка меди MDB после Freerouting, по тексту файла платы.

18.11.2026 (применено, медь потом переразведена проходом 15 — списки сняты, история в git):
- MDB_TX_E отведена от площадки +24 В F3; переход +24V_P F3.1 перенесён в площадку; +5V к Q12.2 / U24.1.
19.11.2026, проход 15:
- поля LCSC/MPN деталей правки берутся из схемы io.kicad_sch (pcbnew в pcb_mdb.py пишет их мимо — без них детали
  выпадают из BOM заводу);
- REMOVE / ADD — доводка после трассировки прохода 15 (если понадобится по DRC).

20.11.2026, Резонит (заказ 116221): переходы в площадках SMD — недопустимо для монтажа. Переходы, у которых отверстие
заходит в окно маски площадки (площадка + 0,05 мм): C21, C30, C41, U5.1, U6.1 — сдвинуты из площадки (MOVE);
C93.2, Q9.3, C114.2 — одиночные переходы GND (сшивка), сняты. Остаются осознанно: тепловые переходы под площадкой U22
(QFN), TP6 (контрольная площадка, без пайки). Проверка — vias_in_pads(), печатается при каждом запуске.

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
    # 20.11.2026: одиночные переходы GND в площадках (Резонит)
    ('via', 'GND', (233.05, 67.334)),   # C93.2
    ('via', 'GND', (268.8, 118.0)),     # Q9.3 (теплоотвод SOT-223)
    ('via', 'GND', (243.5, 64.0)),      # C114.2
]

ADD = []

# (цепь, было, стало): переход и концы его дорожек на обоих слоях
MOVE = [
    ('+3V3', (93.8, 110.075), (94.6, 110.075)),          # C21.1
    ('+5V_LCD2', (55.45, 92.275), (56.55, 92.275)),      # C41.1
    ('+5V_LCD1', (55.45, 62.275), (56.55, 62.275)),      # C30.1
    ('+5V_LCD1', (78.15, 57.45), (78.3, 57.65)),         # U5.1
    ('+5V_LCD2', (78.15, 87.45), (78.3, 87.65)),         # U6.1
]

KEEP = ('U22', 'TP6')   # тепловые переходы QFN; контрольная площадка


def move_vias(b):
    n = 0
    for net, old, new in MOVE:
        for t in b.tracks():
            k, pts, hw, L, nn = b.tinfo(t)
            if nn.split('/')[-1] != net:
                continue
            if k == 'via' and near(pts[0], old):
                at = find(t, 'at')
                at[1], at[2] = new[0], new[1]
                n += 1
            elif k == 'seg':
                for tag in ('start', 'end'):
                    q = find(t, tag)
                    if near((float(q[1]), float(q[2])), old):
                        q[1], q[2] = new[0], new[1]
    return n


def vias_in_pads(b, mask=0.05):
    """Переходы, у которых отверстие заходит в окно маски площадки SMD."""
    vias = []
    for t in b.tracks():
        if t[0] == 'via':
            at = find(t, 'at')
            vias.append((float(at[1]), float(at[2]), float(find(t, 'drill')[1]) / 2))
    out = []
    for r, n, net, (a, c, d, e), f, bb in b.pads():
        if (f and bb) or r in KEEP:
            continue
        for x, y, dr in vias:
            dx, dy = max(a - mask - x, 0, x - d - mask), max(c - mask - y, 0, y - e - mask)
            if (dx * dx + dy * dy) ** 0.5 < dr:
                out.append('%s.%s (%.2f; %.2f)' % (r, n, x, y))
    return out


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
    moved = move_vias(b)
    fields = fix_fields(b)
    b.save()
    print('снято %d, добавлено %d, сдвинуто переходов %d, полей LCSC/MPN %d' % (removed, added, moved, fields))
    bad = vias_in_pads(b)
    print('переходы в площадках SMD:', ', '.join(bad) or 'нет')


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
