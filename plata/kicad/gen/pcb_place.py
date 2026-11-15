"""Раскладка деталей платы (черновая): нетлист + посадочные места → plata/kicad/placement.json и картинка.

Запуск (на ПК, без KiCad): python3 pcb_place.py <mso74-plata.net из ветки kicad-out> <footprints из ветки kicad-libs> [png]
Плату .kicad_pcb из placement.json собирает CI (pcb_build.py, внутри KiCad). Правки раскладки — здесь, не в плате.

Плата 240 × 120 мм («чуть меньше табло» 256 × 127, Павел 14.11), 4 отверстия M3 по углам, на DIN-рейку через
держатель (3D-печать). Вид спереди (сторона деталей); ось Y вниз. Кромки:
  низ  — все клеммы KANGNEX и MDB: провода уходят вниз к вводам модуля табло;
  верх — питание табло Mini-Fit (J3, J4) и шлейф HUB75 (J14) — к матрице;
  право — два RJ45 (сеть и Vendotek) и USB-C (доступ без разборки).
Зоны: слева — питание (24 В, eFuse, 2 × 5 В / 5 А, 12/5/3,3 В); центр сверху — ESP32, часы, буферы табло;
справа сверху — Ethernet: W5500, коммутатор RTL8305NB, RJ45 «Сеть» и «Vendotek», ниже USB; снизу над клеммами — RS-485/RS-232, MDB и монетник/купюрник, расширитель входов-выходов.
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
    'J3': (7, 26, 0), 'J4': (7, 56, 0),     # табло — у левой кромки, напротив выхода своего LM61460 (5 А — короткий путь)
    # ESP32 и USB-UART; кнопки сброса/загрузки — у нижнего края модуля
    'U7': (150, 26, 0), 'SW1': (138, 46, 0), 'SW2': (148, 46, 0),
    'J5': (236.33, 68, 90), 'U9': (224, 68, 90), 'U8': (214, 76, 0),
    # Ethernet: разъём на правой кромке сверху, W5500 рядом
    'J7': (222.74, 22, 90), 'J18': (222.74, 45, 90), 'U10': (196, 22, 0), 'Y1': (186, 22, 0),
    # коммутатор RTL8305NB: между W5500 и двумя RJ45; трансформатор H1102 — связь W5500 ↔ порт 0
    'T1': (180, 42, 90), 'T2': (192, 42, 90), 'U22': (206, 44, 0),
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


# ---------------------------------------------------------------- силовые ячейки DC/DC (аудит Codex C-001)
# Каждый преобразователь — компактная ячейка: керамика VIN/PGND вплотную к выводам, дроссель у SW, выходная керамика у
# дросселя, делитель FB у FB. Раньше входные конденсаторы «тянулись» к eFuse по общей цепи +24V_P (до 75 мм от U5).
# Смещения (dx, dy) — от центра микросхемы; деталь ставится в ближайшее свободное место к этой точке, по порядку списка.
# Проход 12 (Codex C2, §5.1): смещения подобраны по площадкам. LM61460 (поворот 0): VIN/PGND справа сверху и снизу
# (8/9, 12/11), SW — справа по центру, FB/AGND/VCC — слева; 100 нФ — у пар VIN/PGND, дроссель повёрнут выводом SW к ИС.
# LMR51430 (SOT-23-6, поворот 90): снизу GND–SW–VIN, сверху CB–EN–FB; дроссель под ИС выводом SW вверх.
# Запись: (позиция, dx, dy) или (позиция, dx, dy, поворот).
def _lm(c100, c10, cvcc, ccb, rb, rt, en, fb, l, cout, cbulk, led):
    return [(c100[0], 1.0, -2.9), (c100[1], 1.0, 2.9), (c10[0], 1.2, -5.6), (c10[1], 1.2, 5.6), (c10[2], -2.4, -6.0),
            (ccb, -1.8, -3.3), (rb, 0.6, -4.6), (cvcc, -3.7, -0.9), (fb[1], -3.7, 1.0), (fb[0], -3.7, 2.7),
            (rt, -1.4, 3.6), (en[0], -3.6, 4.6), (en[1], -3.6, 6.2), (l, 10.0, 0, 0),
            (cout[0], 19.6, -4.8), (cout[1], 19.6, -1.6), (cout[2], 19.6, 1.6), (cout[3], 19.6, 4.8), (cbulk, 27.5, 0),
            (led[0], 24.5, 8.5), (led[1], 28.5, 8.5)]


def _lmr(cin, cvin, ccb, en, fb, l, ly, cout, cy, cout100, led):
    return [(cvin, 2.6, 0.6), (cin, 5.3, 0.6), (ccb, -2.4, -2.3), (en[0], 0.0, -3.6), (en[1], 0.0, -5.2),
            (fb[0], 2.6, -2.7), (fb[1], 2.6, -4.3), (l, 0.0, ly, 270)] + \
           [(c, -4.0 + 4.0 * i, cy) for i, c in enumerate(cout)] + [(cout100, 7.0, cy - 2.0), (led[0], -8.0, 0.5), (led[1], -8.0, 2.5)]


CELLS = {
    # ячейки LM61460 повёрнуты на 180°: выход (дроссель → 4 × 47 мкФ → 470 мкФ) смотрит влево, к J3/J4 у кромки;
    # вход — вправо, к +24V_P от eFuse. Смещения _lm заданы для поворота 0 и разворачиваются вместе с ИС
    'U5': ((46, 26, 180), _lm(('C26', 'C27'), ('C24', 'C25', 'C110'), 'C28', 'C29', 'R29', 'R28', ('R26', 'R27'),
                            ('R30', 'R31'), 'L4', ('C30', 'C31', 'C32', 'C33'), 'C34', ('R32', 'D9'))),
    'U6': ((46, 56, 180), _lm(('C37', 'C38'), ('C35', 'C36', 'C111'), 'C39', 'C40', 'R36', 'R35', ('R33', 'R34'),
                            ('R37', 'R38'), 'L5', ('C41', 'C42', 'C43', 'C44'), 'C45', ('R39', 'D10'))),
    'U2': ((68, 12, 90), _lmr('C6', 'C7', 'C8', ('R11', 'R12'), ('R13', 'R14'), 'L1', 9.0, ('C9', 'C10', 'C115'), 17.4, 'C11', ('R15', 'D6'))),
    'U3': ((68, 40, 90), _lmr('C12', 'C13', 'C14', ('R16', 'R17'), ('R18', 'R19'), 'L2', 9.0, ('C15', 'C16'), 17.4, 'C17', ('R20', 'D7'))),
    'U4': ((68, 68, 90), _lmr('C18', 'C19', 'C20', ('R21', 'R22'), ('R23', 'R24'), 'L3', 5.8, ('C21', 'C22'), 10.6, 'C23', ('R25', 'D8'))),
}
# Развязка рядом с выводом питания своей микросхемы (позиция → (микросхема, вывод)): ставится после раскладки остального
POST = {'C113': ('U23', '5')}


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


def pads(path):
    """Номер площадки → центр (первая площадка с этим номером), в координатах посадочного места."""
    t = parse(open(path, encoding='utf-8').read())
    t = t[0] if t and isinstance(t[0], list) else t
    out = {}
    for x in t:
        if isinstance(x, list) and x and x[0] == 'pad':
            at = [y for y in x if isinstance(y, list) and y[0] == 'at'][0]
            out.setdefault(str(x[1]), (float(at[1]), float(at[2])))
    return out


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
        self.pads = {r: pads(fp_path(c.fp, fpdir, ownlib)) for r, c in comps.items() if r in {u for u, _ in POST.values()}}
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
            edge = ref in ('J5', 'J7', 'J18', 'J3', 'J4', 'J14')
            if self.free(self.abs_rect(ref, x, y, rot), edge):
                self.put(ref, x, y, rot, edge_ok=edge)
            else:
                r = self.abs_rect(ref, x, y, rot)
                print('сдвинут якорь', ref)
                self.near(ref, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2, rot=rot)

    def cells(self):
        for u, ((ux, uy, urot), parts) in CELLS.items():
            self.put(u, ux, uy, urot)
            for item in parts:
                ref, dx, dy = item[:3]
                r = item[3] if len(item) > 3 else None
                if urot == 180:
                    dx, dy, r = -dx, -dy, (None if r is None else (r + 180) % 360)
                if ref not in self.comps:
                    print('ячейка %s: нет позиции %s в нетлисте — пропуск' % (u, ref))
                    continue
                self.near(ref, ux + dx, uy + dy, step=0.25, rmax=12, rot=r)

    def pad_xy(self, ref, num):
        x, y, rot = self.pos[ref]
        px, py = self.pads[ref][num]
        a = math.radians(rot)
        c, s = round(math.cos(a)), round(math.sin(a))
        return x + px * c + py * s, y - px * s + py * c

    def post(self):
        for ref, (u, pad) in POST.items():
            self.near(ref, *self.pad_xy(u, pad), step=0.25, rmax=10)

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
        todo = [r for r in self.comps if r not in self.pos and r not in POST]
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
              '/MDB и входы/': '#859900', '/Табло и часы/': '#d33682', '/Расширитель входов-выходов/': '#6c71c4', '/Коммутатор Ethernet/': '#268bd2'}
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
    pl.cells()
    pl.anchors()
    pl.place_rest()
    pl.post()
    out = {'board': {'w': W, 'h': H, 'holes': [[HOLE, HOLE], [W - HOLE, HOLE], [HOLE, H - HOLE], [W - HOLE, H - HOLE]]},
           'parts': {r: list(pl.pos[r]) for r in sorted(pl.pos)}}
    with open(os.path.join(os.path.dirname(HERE), 'placement.json'), 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    if png:
        preview(pl, png)
    print('размещено:', len(pl.pos), 'из', len(comps))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
