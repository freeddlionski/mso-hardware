"""Раскладка деталей платы (черновая): нетлист + посадочные места → plata/kicad/placement.json и картинка.

Запуск (на ПК, без KiCad): python3 pcb_place.py <mso74-plata.net из ветки kicad-out> <footprints из ветки kicad-libs> [png]
Плату .kicad_pcb из placement.json собирает CI (pcb_build.py, внутри KiCad). Правки раскладки — здесь, не в плате.

Плата 240 × 120 мм («чуть меньше табло» 256 × 127, Павел 14.11), 4 отверстия M3 по углам, на DIN-рейку через
держатель (3D-печать). Вид спереди (сторона деталей); ось Y вниз. Кромки:
  низ  — все клеммы KANGNEX и MDB: провода уходят вниз к вводам модуля табло;
  верх — питание табло Mini-Fit (J3, J4) и шлейф HUB75 (J14) — к матрице;
  право — RJ45 и USB-C (доступ без разборки).
Зоны: слева — питание (24 В, eFuse, 2 × 5 В / 5 А, 12/5/3,3 В); центр сверху — ESP32, часы, буферы табло;
справа сверху — Ethernet и USB; снизу над клеммами — RS-485/RS-232, MDB и монетник/купюрник, расширитель входов-выходов.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import netlist  # noqa: E402
from sexp import parse  # noqa: E402

W, H = 240.0, 120.0
HOLE = 4.0                     # центр отверстия M3 от края
HOLE_KEEP = 3.6                # радиус запретной зоны (головка винта M3 + зазор)
GAP = 0.3                      # зазор между куртами
POWER = {'GND', '+24V_P', '+12V', '+5V', '+3V3', '+3V3A', '+5V_LCD1', '+5V_LCD2'}

# ---------------------------------------------------------------- якоря: ref → (x, y, поворот°) или правило кромки
# Нижняя кромка: клеммы по группам слева направо; лицевая сторона клеммы — на кромке платы.
BOTTOM = [['J1', 'J2'], ['J9', 'J8'], ['J11', 'J12', 'J10', 'J13'], ['J15', 'J16']]
ANCHORS = {
    # питание: вход снизу слева, 2 × 5 В / 5 А вверху слева, выходы J3/J4 на верхнюю кромку
    'F1': (14, 88, 0), 'D1': (30, 100, 90), 'U1': (34, 84, 0), 'Q1': (46, 84, 0), 'C5': (52, 100, 0),
    'U5': (12, 22, 0), 'L4': (28, 22, 0), 'C34': (46, 20, 0), 'F4': (56, 32, 90),
    'U6': (12, 52, 0), 'L5': (28, 52, 0), 'C45': (46, 50, 0), 'F5': (56, 60, 90),
    'J3': (16, 6, 90), 'J4': (36, 6, 90),
    'U2': (66, 78, 0), 'L1': (66, 88, 0), 'U3': (78, 64, 0), 'L2': (78, 74, 0), 'U4': (66, 64, 0), 'L3': (66, 54, 0),
    # ESP32 и USB-UART; кнопки сброса/загрузки — у нижнего края модуля
    'U7': (150, 26, 0), 'SW1': (138, 46, 0), 'SW2': (148, 46, 0),
    'J5': (236.33, 56, 90), 'U9': (224, 56, 90), 'U8': (214, 66, 0),
    # Ethernet: разъём на правой кромке сверху, W5500 рядом
    'J7': (222.74, 22, 90), 'U10': (196, 22, 0), 'Y1': (186, 22, 0),
    # табло: шлейф HUB75 на верхней кромке, буферы под ним; часы с батарейкой
    'J14': (96, 7, 90), 'U17': (100, 22, 0), 'U18': (114, 22, 0),
    'BT1': (168, 60, 0), 'U19': (154, 60, 0), 'Y2': (154, 67, 0),
    # связь: над своими клеммами
    'U12': (72, 98, 0), 'U11': (92, 98, 0),
    # MDB, монетник, купюрник, сервис
    'U13': (120, 94, 0), 'U14': (128, 94, 0), 'U15': (140, 94, 0), 'U16': (150, 94, 0), 'SW3': (160, 92, 0),
    # расширитель входов-выходов
    'U20': (196, 84, 0), 'U21': (212, 84, 0),
}


# ---------------------------------------------------------------- посадочные места
def fp_path(fp, fpdir, ownlib):
    lib, name = fp.split(':', 1)
    d = ownlib if lib == 'mso74' else os.path.join(fpdir, lib + '.pretty')
    return os.path.join(d, name + '.kicad_mod')


def _pts(node):
    out = []
    for y in node:
        if isinstance(y, list) and y and y[0] in ('start', 'end', 'center', 'xy', 'mid'):
            out.append((float(y[1]), float(y[2])))
        elif isinstance(y, list) and y and y[0] == 'pts':
            out += _pts(y)
    return out


def _arc_pts(node):
    """Крайние точки дуги (start, mid, end): концы + точки окружности на осях внутри дуги."""
    g = {y[0]: (float(y[1]), float(y[2])) for y in node if isinstance(y, list) and y and y[0] in ('start', 'mid', 'end')}
    (x1, y1), (x2, y2), (x3, y3) = g['start'], g['mid'], g['end']
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-9:
        return [g['start'], g['mid'], g['end']]
    ux = ((x1 * x1 + y1 * y1) * (y2 - y3) + (x2 * x2 + y2 * y2) * (y3 - y1) + (x3 * x3 + y3 * y3) * (y1 - y2)) / d
    uy = ((x1 * x1 + y1 * y1) * (x3 - x2) + (x2 * x2 + y2 * y2) * (x1 - x3) + (x3 * x3 + y3 * y3) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    a1, a2, a3 = (math.atan2(y - uy, x - ux) for x, y in (g['start'], g['mid'], g['end']))

    def between(a, b, c):        # c на пути из a в b против часовой
        return (c - a) % (2 * math.pi) <= (b - a) % (2 * math.pi)
    ccw = between(a1, a3, a2)
    out = [g['start'], g['mid'], g['end']]
    for k in range(4):
        ang = k * math.pi / 2
        if (between(a1, a3, ang) if ccw else between(a3, a1, ang)):
            out.append((ux + r * math.cos(ang), uy + r * math.sin(ang)))
    return out


def courtyard(path):
    """Прямоугольник курта (xmin, ymin, xmax, ymax) в координатах посадочного места; без курта — по площадкам + 0,25."""
    t = parse(open(path, encoding='utf-8').read())
    t = t[0] if t and isinstance(t[0], list) else t
    pts = []
    for x in t:
        if isinstance(x, list) and x and str(x[0]).startswith('fp_'):
            if any(isinstance(y, list) and y[0] == 'layer' and y[1] == 'F.CrtYd' for y in x):
                if x[0] == 'fp_circle':
                    c = [y for y in x if isinstance(y, list) and y[0] == 'center'][0]
                    e = [y for y in x if isinstance(y, list) and y[0] == 'end'][0]
                    r = math.hypot(float(e[1]) - float(c[1]), float(e[2]) - float(c[2]))
                    pts += [(float(c[1]) - r, float(c[2]) - r), (float(c[1]) + r, float(c[2]) + r)]
                elif x[0] == 'fp_arc':
                    pts += _arc_pts(x)
                else:
                    pts += _pts(x)
    if not pts:
        for x in t:
            if isinstance(x, list) and x and x[0] == 'pad':
                at = [y for y in x if isinstance(y, list) and y[0] == 'at'][0]
                sz = [y for y in x if isinstance(y, list) and y[0] == 'size'][0]
                px, py, sx, sy = float(at[1]), float(at[2]), float(sz[1]) / 2 + 0.25, float(sz[2]) / 2 + 0.25
                pts += [(px - sx, py - sy), (px + sx, py + sy)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def rot_box(box, rot):
    """Повернуть прямоугольник посадочного места (KiCad: угол против часовой при Y вниз)."""
    x0, y0, x1, y1 = box
    a = math.radians(rot)
    c, s = round(math.cos(a)), round(math.sin(a))
    pts = [(x * c + y * s, -x * s + y * c) for x in (x0, x1) for y in (y0, y1)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- раскладка
class Placer:
    def __init__(self, comps, fpdir, ownlib):
        self.comps = comps
        self.box = {r: courtyard(fp_path(c.fp, fpdir, ownlib)) for r, c in comps.items()}
        self.pos = {}           # ref → (x, y, rot)
        self.rects = []         # (x0, y0, x1, y1, ref)
        for hx, hy in ((HOLE, HOLE), (W - HOLE, HOLE), (HOLE, H - HOLE), (W - HOLE, H - HOLE)):
            self.rects.append((hx - HOLE_KEEP, hy - HOLE_KEEP, hx + HOLE_KEEP, hy + HOLE_KEEP, 'H'))

    def abs_rect(self, ref, x, y, rot):
        b = rot_box(self.box[ref], rot)
        return x + b[0], y + b[1], x + b[2], y + b[3]

    def free(self, r, edge_ok=False):
        x0, y0, x1, y1 = r
        if not edge_ok and (x0 < 0.5 or y0 < 0.5 or x1 > W - 0.5 or y1 > H - 0.5):
            return False
        for a in self.rects:
            if x0 < a[2] + GAP and a[0] < x1 + GAP and y0 < a[3] + GAP and a[1] < y1 + GAP:
                return False
        return True

    def put(self, ref, x, y, rot, edge_ok=False, force=False):
        r = self.abs_rect(ref, x, y, rot)
        if not force and not self.free(r, edge_ok):
            hit = [a[4] for a in self.rects
                   if r[0] < a[2] + GAP and a[0] < r[2] + GAP and r[1] < a[3] + GAP and a[1] < r[3] + GAP]
            raise SystemExit('Якорь %s не помещается: пересекается с %s (%.1f %.1f %.1f %.1f)' % ((ref, hit) + r))
        self.pos[ref] = (round(x, 3), round(y, 3), rot)
        self.rects.append(r + (ref,))

    def bottom_edge(self):
        """Клеммы на нижнюю кромку: лицевая сторона (низ корпуса Fab ≈ низ курта − 0,5) на краю платы."""
        groups = []
        for g in BOTTOM:
            groups.append([(ref, self.box[ref]) for ref in g])
        inner = 2.0
        widths = [sum(b[2] - b[0] for _, b in g) + inner * (len(g) - 1) for g in groups]
        x_left, x_right = HOLE + HOLE_KEEP + 1.0, W - HOLE - HOLE_KEEP - 1.0
        gap = (x_right - x_left - sum(widths)) / (len(groups) - 1)
        x = x_left
        for g, w in zip(groups, widths):
            for ref, b in g:
                ox = x - b[0]
                oy = H + 0.5 - b[3]          # курт на 0,5 за край: корпус клеммы — по краю
                if self.comps[ref].fp.endswith('Vertical'):
                    oy = H - 1.0 - b[3]      # Mini-Fit (MDB) — вертикальный, целиком на плате
                self.put(ref, ox, oy, 0, edge_ok=True)
                x += b[2] - b[0] + inner
            x += gap - inner

    def anchors(self):
        for ref, (x, y, rot) in ANCHORS.items():
            if ref not in self.comps:
                continue
            edge = ref in ('J5', 'J7', 'J3', 'J4', 'J14')
            if self.free(self.abs_rect(ref, x, y, rot), edge):
                self.put(ref, x, y, rot, edge_ok=edge)
            else:
                r = self.abs_rect(ref, x, y, rot)
                print('сдвинут якорь', ref)
                self.near(ref, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, rot=rot)

    def owner(self, ref):
        """Якорь, к которому тянется деталь: больше всего общих цепей (сигнальные ×4, питание ×1, без GND)."""
        c = self.comps[ref]
        best, score = None, 0
        nets = set(c.pins.values()) - {'GND'}
        for a in self.pos:
            ca = self.comps.get(a)
            if not ca:
                continue
            common = nets & set(ca.pins.values())
            s = sum(1 if n in POWER else 4 for n in common)
            if ca.sheet != c.sheet:
                s *= 0.3
            if s > score:
                best, score = a, s
        return best, score

    def place_rest(self):
        todo = [r for r in self.comps if r not in self.pos]
        # сначала те, у кого связь с якорем сильнее; связанные по цепочке (R→C→…) подтянутся следом
        for _ in range(len(todo)):
            if not todo:
                break
            ranked = sorted(((self.owner(r), r) for r in todo), key=lambda t: -t[0][1])
            (anchor, score), ref = ranked[0]
            todo.remove(ref)
            if anchor is None:
                anchor = 'U7'
            ax, ay, _ = self.pos[anchor]
            ar = [a for a in self.rects if a[4] == anchor][0]
            cx, cy = (ar[0] + ar[2]) / 2, (ar[1] + ar[3]) / 2
            self.near(ref, cx, cy)

    def near(self, ref, cx, cy, step=0.5, rmax=60, rot=None):
        b = self.box[ref]
        rots = (rot,) if rot is not None else ((0, 90) if len(self.comps[ref].pins) <= 3 else (0,))
        cand = []
        n = int(rmax / step)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                d = (i * step) ** 2 + (j * step) ** 2
                if d <= rmax * rmax:
                    cand.append((d, cx + i * step, cy + j * step))
        cand.sort()
        for d, x, y in cand:
            for rot in rots:
                bb = rot_box(b, rot)
                ox, oy = x - (bb[0] + bb[2]) / 2, y - (bb[1] + bb[3]) / 2
                if self.free(self.abs_rect(ref, ox, oy, rot)):
                    self.put(ref, ox, oy, rot)
                    return
        raise SystemExit('Нет места для %s' % ref)


def preview(pl, png):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle, Circle
    colors = {'/Питание/': '#e07b39', '/ESP32-S3 и USB/': '#3a7bd5', '/Ethernet/': '#2aa198', '/RS-485 и RS-232/': '#b58900',
              '/MDB и входы/': '#859900', '/Табло и часы/': '#d33682', '/Расширитель входов-выходов/': '#6c71c4'}
    fig, ax = plt.subplots(figsize=(16, 8.6))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=2, ec='black'))
    for hx, hy in ((HOLE, HOLE), (W - HOLE, HOLE), (HOLE, H - HOLE), (W - HOLE, H - HOLE)):
        ax.add_patch(Circle((hx, hy), 1.6, fc='white', ec='black'))
        ax.add_patch(Circle((hx, hy), HOLE_KEEP, fill=False, ls=':', ec='gray'))
    for x0, y0, x1, y1, ref in pl.rects:
        if ref == 'H':
            continue
        c = pl.comps[ref]
        col = colors.get(c.sheet, 'gray')
        big = (x1 - x0) * (y1 - y0) > 30 or ref in ANCHORS or ref.startswith('J')
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=col, alpha=0.55 if big else 0.3, ec=col, lw=0.6))
        if big:
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, ref, ha='center', va='center', fontsize=7, weight='bold')
    for s, col in colors.items():
        ax.plot([], [], 's', color=col, label=s.strip('/'))
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.02), ncol=4, fontsize=9, frameon=False)
    ax.set_xlim(-3, W + 3)
    ax.set_ylim(H + 3, -3)
    ax.set_aspect('equal')
    ax.set_title('Плата МСО74, раскладка-черновик 240 × 120 мм, вид со стороны деталей (низ — клеммы, верх — к матрице)')
    plt.savefig(png, dpi=110, bbox_inches='tight')


def main(netpath, fpdir, png=None):
    comps, _ = netlist.read(netpath)
    ownlib = os.path.join(os.path.dirname(HERE), 'lib', 'mso74.pretty')
    pl = Placer(comps, fpdir, ownlib)
    pl.bottom_edge()
    pl.anchors()
    pl.place_rest()
    out = {'board': {'w': W, 'h': H, 'holes': [[HOLE, HOLE], [W - HOLE, HOLE], [HOLE, H - HOLE], [W - HOLE, H - HOLE]]},
           'parts': {r: list(pl.pos[r]) for r in sorted(pl.pos)}}
    with open(os.path.join(os.path.dirname(HERE), 'placement.json'), 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    if png:
        preview(pl, png)
    print('размещено:', len(pl.pos), 'из', len(comps))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
