"""Правка готовой платы по тексту файла (S-выражения), без pcbnew: снятие деталей и меди, дочистка висящих концов.

  python3 eco_text.py clean BOARD.kicad_pcb ECO.json   — снять детали из ECO['remove_refs'] и медь: цепей, которых нет,
                                                          чужую под площадками новых деталей, прежних цепей на площадках
                                                          со сменившейся цепью; дальше — висящие концы по цепочке.
                                                          В ECO.json дописывается 'touched' — цепи, которые надо развести.
  python3 eco_text.py prune BOARD.kicad_pcb ECO.json   — после трассировки: висящие концы цепей ECO['touched'] по всей плате.

Почему не pcbnew: в Python-обёртке KiCad 9 board.Remove() отдаёт объект во владение Python, и дальше плата портилась
(«SwigPyObject is not iterable», падение 139 — прогоны 44379977742…44383088146 ветки feat/mdb-standard). Текст файла —
детерминированно и проверяется локально.
"""
import json
import math
import sys
from pathlib import Path

from sexp import Q, dump, find, findall, parse

CLR = 0.2           # зазор, мм
EPS = 0.02          # совпадение концов, мм
PLANES = ('GND', '+3V3', '+24V_P')


# ---------- геометрия ----------
def rot(x, y, a):
    r = math.radians(a)
    return x * math.cos(r) + y * math.sin(r), -x * math.sin(r) + y * math.cos(r)


def d_pt_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def d_pt_rect(x, y, r):
    return math.hypot(max(r[0] - x, 0, x - r[2]), max(r[1] - y, 0, y - r[3]))


def _cross(a, b, c, d):
    def o(p, q, s):
        return (q[0] - p[0]) * (s[1] - p[1]) - (q[1] - p[1]) * (s[0] - p[0])
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def d_seg_rect(ax, ay, bx, by, r):
    if (r[0] <= ax <= r[2] and r[1] <= ay <= r[3]) or (r[0] <= bx <= r[2] and r[1] <= by <= r[3]):
        return 0.0
    cs = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    if any(_cross((ax, ay), (bx, by), cs[i], cs[(i + 1) % 4]) for i in range(4)):
        return 0.0
    return min([d_pt_rect(ax, ay, r), d_pt_rect(bx, by, r)] + [d_pt_seg(cx, cy, ax, ay, bx, by) for cx, cy in cs])


def in_poly(x, y, pts):
    inside = False
    j = len(pts) - 1
    for i in range(len(pts)):
        xi, yi = pts[i]
        xj, yj = pts[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


# ---------- плата ----------
class Board:
    def __init__(self, path):
        self.path = Path(path)
        self.tree = parse(self.path.read_text(encoding='utf-8'))
        self.nets = {n[1]: str(n[2]) for n in findall(self.tree, 'net') if len(n) > 2}
        self.net_no = {v: k for k, v in self.nets.items()}

    def save(self):
        self.path.write_text(dump(self.tree) + '\n', encoding='utf-8')

    def netname(self, node):
        n = find(node, 'net')
        if not n:
            return ''
        return str(n[2]) if len(n) > 2 else self.nets.get(n[1], '')

    @staticmethod
    def ref(fp):
        for p in findall(fp, 'property'):
            if p[1] == 'Reference':
                return str(p[2])
        return ''

    def footprints(self):
        return findall(self.tree, 'footprint')

    def pads(self, skip_refs=()):
        """[(ref, номер, цепь, рамка, на F.Cu, на B.Cu)] — рамка по осям с учётом поворота площадки."""
        out = []
        for fp in self.footprints():
            r = self.ref(fp)
            if r in skip_refs:
                continue
            at = find(fp, 'at')
            X, Y = float(at[1]), float(at[2])
            A = float(at[3]) if len(at) > 3 else 0.0
            for p in findall(fp, 'pad'):
                pa, sz = find(p, 'at'), find(p, 'size')
                dx, dy = rot(float(pa[1]), float(pa[2]), A)
                ang = float(pa[3]) if len(pa) > 3 else A
                w, h = float(sz[1]), float(sz[2])
                c, s = abs(math.cos(math.radians(ang))), abs(math.sin(math.radians(ang)))
                hw, hh = (w * c + h * s) / 2, (w * s + h * c) / 2
                cx, cy = X + dx, Y + dy
                layers = [str(x) for x in (find(p, 'layers') or [])[1:]]
                onf = any(L in ('F.Cu', '*.Cu') for L in layers)
                onb = any(L in ('B.Cu', '*.Cu') for L in layers)
                out.append((r, str(p[1]), self.netname(p), (cx - hw, cy - hh, cx + hw, cy + hh), onf, onb))
        return out

    def tracks(self):
        return [n for n in self.tree if isinstance(n, list) and n and n[0] in ('segment', 'via')]

    def tinfo(self, n):
        """(вид, точки, полуширина, слой, цепь)."""
        if n[0] == 'via':
            at = find(n, 'at')
            return ('via', [(float(at[1]), float(at[2]))], float(find(n, 'size')[1]) / 2, None, self.netname(n))
        a, e = find(n, 'start'), find(n, 'end')
        return ('seg', [(float(a[1]), float(a[2])), (float(e[1]), float(e[2]))], float(find(n, 'width')[1]) / 2,
                str(find(n, 'layer')[1]), self.netname(n))

    def zones_filled(self):
        """{(цепь, слой): [многоугольники]}."""
        out = {}
        for z in findall(self.tree, 'zone'):
            if find(z, 'keepout'):
                continue
            net = self.netname(z) or str((find(z, 'net_name') or ['', ''])[1])
            for fpoly in findall(z, 'filled_polygon'):
                L = str(find(fpoly, 'layer')[1])
                pts = [(float(q[1]), float(q[2])) for q in findall(find(fpoly, 'pts'), 'xy')]
                out.setdefault((net, L), []).append(pts)
        return out

    def remove(self, node):
        for i, x in enumerate(self.tree):
            if x is node:
                del self.tree[i]
                return True
        return False


def close(p, q, r=EPS):
    return math.hypot(p[0] - q[0], p[1] - q[1]) <= r


class Cleaner:
    def __init__(self, b):
        self.b = b
        self.pads = b.pads()
        self.zones = b.zones_filled()
        self.removed = []

    def info(self, n):
        return self.b.tinfo(n)

    def anchored(self, pt, net, node):
        kind, pts, hw, layer, _ = self.info(node)
        for _, _, n, r, onf, onb in self.pads:
            if n == net and r[0] <= pt[0] <= r[2] and r[1] <= pt[1] <= r[3]:
                if kind == 'via' or (layer == 'F.Cu' and onf) or (layer == 'B.Cu' and onb):
                    return True
        layers = ['F.Cu', 'B.Cu', 'In1.Cu', 'In2.Cu'] if kind == 'via' else [layer]
        for L in layers:
            for poly in self.zones.get((net, L), []):
                if in_poly(pt[0], pt[1], poly):
                    return True
        for o in self.b.tracks():
            if o is node:
                continue
            ok, opts, ohw, olayer, onet = self.info(o)
            if onet != net:
                continue
            if ok == 'via':
                if close(opts[0], pt, ohw):
                    return True
            elif kind == 'via' or olayer == layer:
                if close(opts[0], opts[1], 1e-6):
                    continue                                   # отрезок нулевой длины — не опора
                if close(opts[0], pt) or close(opts[1], pt) or d_pt_seg(pt[0], pt[1], *opts[0], *opts[1]) <= ohw:
                    return True
        return False

    def drop(self, node, queue, why=''):
        kind, pts, hw, layer, net = self.info(node)
        self.b.remove(node)
        self.removed.append((kind, pts, net, why))
        for o in list(self.b.tracks()):                         # отрезки нулевой длины той же цепи на концах
            ok, opts, _, _, onet = self.info(o)
            if ok == 'seg' and onet == net and close(opts[0], opts[1], 1e-6) and any(close(opts[0], p) for p in pts):
                self.b.remove(o)
                self.removed.append((ok, opts, onet, 'нулевой'))
        queue += [(p, net) for p in pts]

    def prune(self, queue=None, nets=None):
        """Висящие концы — от точек очереди или по цепям nets на всей плате."""
        while True:
            if queue is not None:
                if not queue:
                    return
                pts = queue[:]
                del queue[:]
                cand = [n for n in self.b.tracks() for p, net in pts
                        if self.info(n)[4] == net and any(close(q, p, self.info(n)[2] if n[0] == 'via' else EPS)
                                                          for q in self.info(n)[1])]
            else:
                cand = [n for n in self.b.tracks() if self.info(n)[4] in nets]
            changed = False
            seen = set()
            q = queue if queue is not None else []
            for n in cand:
                if id(n) in seen or not any(x is n for x in self.b.tree):
                    continue
                seen.add(id(n))
                kind, pts, hw, layer, net = self.info(n)
                if kind == 'via':
                    if any(pn == net and r[0] <= pts[0][0] <= r[2] and r[1] <= pts[0][1] <= r[3]
                           for _, _, pn, r, _, _ in self.pads):
                        continue
                    cnt = 0
                    for o in self.b.tracks():
                        ok, opts, _, _, onet = self.info(o)
                        if ok == 'seg' and onet == net and not close(opts[0], opts[1], 1e-6) and \
                                (close(opts[0], pts[0], hw) or close(opts[1], pts[0], hw)):
                            cnt += 1
                    if cnt == 0 or (cnt == 1 and net not in PLANES):
                        self.drop(n, q, 'висящий переход')
                        changed = True
                    continue
                if close(pts[0], pts[1], 1e-6):
                    continue
                if all(self.anchored(p, net, n) for p in pts):
                    continue
                self.drop(n, q, 'висящий конец')
                changed = True
            if queue is None and not changed:
                return


def clean(board_path, eco_path):
    eco = json.load(open(eco_path, encoding='utf-8'))
    b = Board(board_path)
    want_nets = set(eco['nets'])
    # 1) снятые детали: их площадки — точки, где медь прежних цепей снимается вся
    seeds = []
    for fp in list(b.footprints()):
        if b.ref(fp) in eco['remove_refs']:
            for r, num, net, rect, _, _ in b.pads():
                if r == b.ref(fp) and net:
                    seeds.append((net, rect))
            b.remove(fp)
            print('снята деталь', b.ref(fp))
    c = Cleaner(b)
    queue = []
    # 1а) точечно: элементы меди из ECO['remove_items'] — ('via', цепь, (x, y)) или ('seg', цепь, (x1, y1), (x2, y2))
    for spec in eco.get('remove_items', []):
        hit = None
        for n in b.tracks():
            kind, pts, hw, layer, net = c.info(n)
            if kind != spec[0] or net != spec[1]:
                continue
            want = [tuple(p) for p in spec[2:]]
            if all(any(close(p, q) for q in pts) for p in want):
                hit = n
                break
        if hit is None:
            print('нет (уже снято?):', spec)
            continue
        b.remove(hit)
        c.removed.append((spec[0], [tuple(p) for p in spec[2:]], spec[1], 'по списку'))
        print('снято по списку:', spec)
    # 1б) медь цепей ECO['rip'] в рамке — развести заново: [цепь, (x0, y0, x1, y1)]
    for net, box in eco.get('rip', []):
        for n in list(b.tracks()):
            kind, pts, hw, layer, tnet = c.info(n)
            if tnet == net and any(box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3] for p in pts) \
                    and any(x is n for x in b.tree):
                c.drop(n, queue, 'переразводка')
    # 2) медь цепей, которых нет в схеме
    for n in list(b.tracks()):
        net = c.info(n)[4]
        if net and net not in want_nets:
            c.drop(n, queue, 'цепи нет в схеме')
    # 3) чужая медь под площадками новых деталей (F.Cu и переходы), зазор CLR
    new_pads = [x for x in c.pads if x[0] in eco['new_refs']]
    for n in list(b.tracks()):
        kind, pts, hw, layer, net = c.info(n)
        if kind == 'seg' and layer != 'F.Cu':
            continue
        for r, num, pnet, rect, _, _ in new_pads:
            if net == pnet:
                continue
            d = (d_pt_rect(pts[0][0], pts[0][1], rect) if kind == 'via'
                 else d_seg_rect(pts[0][0], pts[0][1], pts[1][0], pts[1][1], rect))
            if d - hw < CLR:
                print('под %s.%s снято: %s %s %s' % (r, num, kind, [tuple(round(v, 3) for v in p) for p in pts], net))
                c.drop(n, queue, 'под новой деталью')
                break
    # 4) медь прежней цепи на площадках со сменившейся цепью
    for r, num, old, new in eco['changed_pads']:
        rect = next(x[3] for x in c.pads if x[0] == r and x[1] == num)
        seeds.append((old, rect))
    for net, rect in seeds:
        for n in list(b.tracks()):
            kind, pts, hw, layer, tnet = c.info(n)
            if tnet != net:
                continue
            hit = (d_pt_rect(pts[0][0], pts[0][1], rect) <= hw) if kind == 'via' else \
                any(rect[0] <= p[0] <= rect[2] and rect[1] <= p[1] <= rect[3] for p in pts)
            if hit and any(x is n for x in b.tree):
                c.drop(n, queue, 'прежняя цепь на площадке')
    c.prune(queue=queue)
    touched = sorted({net for _, _, net, _ in c.removed} | set(eco.get('touched', [])))
    eco['touched'] = touched
    json.dump(eco, open(eco_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    b.save()
    print('снято элементов меди: %d; цепи правки: %s' % (len(c.removed), ', '.join(touched)))


def prune_after(board_path, eco_path):
    eco = json.load(open(eco_path, encoding='utf-8'))
    b = Board(board_path)
    c = Cleaner(b)
    nets = {n for n in eco['touched'] if n not in PLANES}
    c.prune(nets=nets)
    for kind, pts, net, why in c.removed:
        print('дочищено: %s %s %s (%s)' % (kind, [tuple(round(v, 3) for v in p) for p in pts], net, why))
    b.save()
    print('дочищено висящих после трассировки:', len(c.removed))


if __name__ == '__main__':
    {'clean': clean, 'prune': prune_after}[sys.argv[1]](*sys.argv[2:4])
