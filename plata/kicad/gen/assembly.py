"""Сборочный чертёж платы (PDF, A3) — для заводов в России.

python3 assembly.py BOARD.kicad_pcb OUT.pdf

Лист 1 — общий вид (М 1,5:1), лист 2 — технические требования, листы 3–6 — четверти платы (М 3:1).
Рисуется: контур платы, контуры корпусов (слой F.Fab, где его нет — площадки), площадки, позиционные обозначения
(размер подгоняется под корпус). Красная площадка — вывод 1 ИМС и разъёмов, катод диодов, «+» электролитических
конденсаторов. DNP — перечёркнуты, подпись «НЕ УСТ.». Шрифт DejaVu (кириллица).
"""
import math
import re
import sys
from datetime import date
from pathlib import Path

from reportlab.lib.colors import Color, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).parent))
from sexp import parse, find, findall  # noqa: E402

MM = 72 / 25.4
A3 = (420, 297)
TITLE = 'Плата контроллера МСО74'
CODE = 'МСО74.ПЛ.A СБ'
AUTHOR = 'Кольман П.'
RED = Color(0.85, 0.1, 0.1)
PAD = Color(0.80, 0.80, 0.80)
FAB = Color(0.25, 0.25, 0.25)
DNPC = Color(0.15, 0.35, 0.85)
POLAR = ('U', 'Q', 'D', 'Y', 'T', 'J', 'BT')      # отмечаем вывод 1


def font():
    for d in ('/usr/share/fonts/truetype/dejavu', '/usr/share/fonts/TTF', '/usr/share/fonts/dejavu'):
        if Path(d, 'DejaVuSans.ttf').exists():
            pdfmetrics.registerFont(TTFont('F', f'{d}/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('FB', f'{d}/DejaVuSans-Bold.ttf'))
            return
    raise SystemExit('нет шрифта DejaVuSans')


def num(n, k):
    v = find(n, k)
    return (float(v[1]), float(v[2])) if v else None


def width(n):
    s = find(n, 'stroke')
    w = find(s, 'width') if s else find(n, 'width')
    return float(w[1]) if w else 0.1


def filled(n):
    f = find(n, 'fill')
    return bool(f) and f[1] in ('yes', 'solid')


def arc3(a, m, b, steps=24):
    """Дуга по трём точкам → ломаная."""
    (x1, y1), (x2, y2), (x3, y3) = a, m, b
    d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
    if abs(d) < 1e-9:
        return [a, b]
    ux = ((x1 ** 2 + y1 ** 2) * (y2 - y3) + (x2 ** 2 + y2 ** 2) * (y3 - y1) + (x3 ** 2 + y3 ** 2) * (y1 - y2)) / d
    uy = ((x1 ** 2 + y1 ** 2) * (x3 - x2) + (x2 ** 2 + y2 ** 2) * (x1 - x3) + (x3 ** 2 + y3 ** 2) * (x2 - x1)) / d
    r = math.hypot(x1 - ux, y1 - uy)
    t1, t2, t3 = (math.atan2(y - uy, x - ux) for x, y in (a, m, b))
    def norm(t):
        return (t - t1) % (2 * math.pi)
    span = norm(t3)
    if norm(t2) > span:
        span -= 2 * math.pi
    return [(ux + r * math.cos(t1 + span * i / steps), uy + r * math.sin(t1 + span * i / steps)) for i in range(steps + 1)]


class Part:
    def __init__(self, fp):
        p = {x[1]: x[2] for x in findall(fp, 'property')}
        self.ref = p['Reference']
        self.pre = re.match(r'[A-Z]+', self.ref).group()
        at = find(fp, 'at')
        self.X, self.Y = float(at[1]), float(at[2])
        self.a = float(at[3]) if len(at) > 3 else 0.0
        attr = (find(fp, 'attr') or [])[1:]
        self.dnp = 'dnp' in attr
        self.nobom = 'exclude_from_bom' in attr
        self.cp = fp[1].split(':')[-1].startswith('CP_')
        self.shapes = []     # (kind, pts, w, filled) в координатах платы
        self.pads = []       # (shape, cx, cy, w, h, ang, name, hole)
        for n in fp[1:]:
            if not isinstance(n, list) or not n or not n[0].startswith('fp_'):
                continue
            l = find(n, 'layer')
            if not l or l[1] != 'F.Fab':
                continue
            k, w = n[0], width(n)
            if k == 'fp_line':
                self.shapes.append(('l', [self.t(*num(n, 'start')), self.t(*num(n, 'end'))], w, False))
            elif k == 'fp_rect':
                (x1, y1), (x2, y2) = num(n, 'start'), num(n, 'end')
                self.shapes.append(('p', [self.t(x, y) for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1))], w, filled(n)))
            elif k == 'fp_circle':
                c, e = num(n, 'center'), num(n, 'end')
                r = math.hypot(e[0] - c[0], e[1] - c[1])
                self.shapes.append(('p', [self.t(c[0] + r * math.cos(i * math.pi / 16), c[1] + r * math.sin(i * math.pi / 16))
                                          for i in range(33)], w, filled(n)))
            elif k == 'fp_arc':
                self.shapes.append(('l', [self.t(*q) for q in arc3(num(n, 'start'), num(n, 'mid'), num(n, 'end'))], w, False))
            elif k == 'fp_poly':
                pts = [self.t(float(q[1]), float(q[2])) for q in findall(find(n, 'pts'), 'xy')]
                self.shapes.append(('p', pts + pts[:1], w, filled(n)))
        for p in findall(fp, 'pad'):
            layers = (find(p, 'layers') or [])[1:]
            if not any(l in ('F.Cu', '*.Cu') for l in layers):
                continue
            pa = find(p, 'at')
            dr = find(p, 'drill')
            if p[2] == 'thru_hole' and dr and float(dr[2] if dr[1] == 'oval' else dr[1]) < 0.6:
                continue                                          # переходы под корпусом
            cx, cy = self.t(float(pa[1]), float(pa[2]))
            sz = find(p, 'size')
            hole = float(dr[2] if dr[1] == 'oval' else dr[1]) if dr else 0
            self.pads.append((p[3], cx, cy, float(sz[1]), float(sz[2]), float(pa[3]) if len(pa) > 3 else 0.0, p[1], hole))
        pts = [q for s in self.shapes for q in s[1]] or [(c[1] + dx * c[3] / 2, c[2] + dy * c[4] / 2)
                                                         for c in self.pads for dx in (-1, 1) for dy in (-1, 1)]
        pts = pts or [(self.X - 0.5, self.Y - 0.5), (self.X + 0.5, self.Y + 0.5)]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        self.box = (min(xs), min(ys), max(xs), max(ys))
        # поле подписи: корпус вместе с площадками
        for c in self.pads:
            r = max(c[3], c[4]) / 2 if self.pre in ('R', 'C', 'D', 'L', 'F', 'FB') else 0
            xs += [c[1] - r, c[1] + r]
            ys += [c[2] - r, c[2] + r]
        self.lbox = (min(xs), min(ys), max(xs), max(ys))

    def t(self, x, y):
        r = math.radians(self.a)
        return self.X + x * math.cos(r) + y * math.sin(r), self.Y - x * math.sin(r) + y * math.cos(r)

    def pin1(self, name):
        return (self.pre in POLAR or self.cp) and name in ('1', 'A1') and not self.nobom


class Sheet:
    """Окно платы (x0, y0, w, h) в масштабе s, левый верхний угол на бумаге (px, py), мм."""

    def __init__(self, c, win, s, px, py):
        self.c, self.win, self.s, self.px, self.py = c, win, s, px, py

    def P(self, x, y):
        return (self.px + (x - self.win[0]) * self.s) * MM, (A3[1] - (self.py + (y - self.win[1]) * self.s)) * MM

    def clip(self):
        x0, y0, w, h = self.win
        p = self.c.beginPath()
        (ax, ay), (bx, by) = self.P(x0, y0), self.P(x0 + w, y0 + h)
        p.rect(ax, by, bx - ax, ay - by)
        self.c.clipPath(p, stroke=0, fill=0)

    def poly(self, pts, w, fill=False, color=black, close=False):
        c = self.c
        c.setStrokeColor(color)
        c.setFillColor(color)
        c.setLineWidth(max(w * self.s, 0.12) * MM)
        p = c.beginPath()
        p.moveTo(*self.P(*pts[0]))
        for q in pts[1:]:
            p.lineTo(*self.P(*q))
        if close or fill:
            p.close()
        c.drawPath(p, stroke=1, fill=1 if fill else 0)

    def pad(self, shape, cx, cy, w, h, ang, hole, color):
        c = self.c
        c.saveState()
        c.translate(*self.P(cx, cy))
        c.rotate(ang)
        c.setFillColor(color)
        c.setStrokeColor(Color(0.45, 0.45, 0.45))
        c.setLineWidth(0.08 * MM)
        W, H = w * self.s * MM, h * self.s * MM
        if shape == 'circle':
            c.circle(0, 0, W / 2, stroke=1, fill=1)
        elif shape == 'oval' or shape == 'roundrect':
            c.roundRect(-W / 2, -H / 2, W, H, min(W, H) / 2 if shape == 'oval' else min(W, H) * 0.25, stroke=1, fill=1)
        else:
            c.rect(-W / 2, -H / 2, W, H, stroke=1, fill=1)
        if hole:
            c.setFillColor(white)
            c.circle(0, 0, hole * self.s * MM / 2, stroke=0, fill=1)
        c.restoreState()

    def label(self, part, maxf, minf):
        x1, y1, x2, y2 = part.lbox
        w, h = (x2 - x1) * self.s, (y2 - y1) * self.s
        txt = part.ref
        k = pdfmetrics.stringWidth(txt, 'FB', 1)                 # ширина строки на 1 мм кегля, мм
        horiz = min(maxf, h * 0.95, w * 0.95 / k)
        vert = min(maxf, w * 0.95, h * 0.95 / k)
        size, rot = (horiz, 0) if horiz >= vert else (vert, 90)
        size = max(size, minf)
        c = self.c
        c.saveState()
        c.translate(*self.P((x1 + x2) / 2, (y1 + y2) / 2))
        c.rotate(rot)
        c.setFont('FB', size * MM)
        tw = pdfmetrics.stringWidth(txt, 'FB', size * MM)
        c.setFillColor(Color(1, 1, 1, alpha=0.75))
        c.rect(-tw / 2 - 0.15 * MM, -size * 0.36 * MM, tw + 0.3 * MM, size * 0.95 * MM, stroke=0, fill=1)
        c.setFillColor(DNPC if part.dnp else black)
        c.drawCentredString(0, -size * 0.3 * MM, txt)
        if part.dnp:
            c.setFont('FB', size * 0.6 * MM)
            c.drawCentredString(0, -size * 1.25 * MM, 'НЕ УСТ.')
        c.restoreState()

    def board(self, edges, parts, maxf, minf):
        c = self.c
        c.saveState()
        self.clip()
        for e in edges:
            self.poly(e, 0.25 / self.s * 1.6, color=black)
        for p in parts:
            for pd in p.pads:
                self.pad(pd[0], pd[1], pd[2], pd[3], pd[4], pd[5], pd[7], RED if p.pin1(pd[6]) else PAD)
        for p in parts:
            col = DNPC if p.dnp else FAB
            for k, pts, w, f in p.shapes:
                self.poly(pts, 0.1, fill=f, color=col)
            if p.dnp:
                x1, y1, x2, y2 = p.box
                self.poly([(x1, y1), (x2, y2)], 0.1, color=DNPC)
                self.poly([(x1, y2), (x2, y1)], 0.1, color=DNPC)
        for p in parts:
            if p.pre != 'H':
                self.label(p, maxf, minf)
        c.restoreState()


def edges_of(b):
    out = []
    for n in b:
        if not isinstance(n, list) or not n or not n[0].startswith('gr_'):
            continue
        l = find(n, 'layer')
        if not l or l[1] != 'Edge.Cuts':
            continue
        if n[0] == 'gr_line':
            out.append([num(n, 'start'), num(n, 'end')])
        elif n[0] == 'gr_arc':
            out.append(arc3(num(n, 'start'), num(n, 'mid'), num(n, 'end')))
        elif n[0] == 'gr_rect':
            (x1, y1), (x2, y2) = num(n, 'start'), num(n, 'end')
            out.append([(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)])
        elif n[0] == 'gr_circle':
            cc, e = num(n, 'center'), num(n, 'end')
            r = math.hypot(e[0] - cc[0], e[1] - cc[1])
            out.append([(cc[0] + r * math.cos(i * math.pi / 24), cc[1] + r * math.sin(i * math.pi / 24)) for i in range(49)])
    return out


def frame(c, sheet, total, name, scale):
    """Рамка (поле 20 мм слева, 5 мм — остальные) и упрощённая основная надпись 185 × 40 мм."""
    c.setStrokeColor(black)
    c.setLineWidth(0.6 * MM)
    c.rect(20 * MM, 5 * MM, 395 * MM, 287 * MM)
    x0, y0, W = 230, 5, 185
    c.rect(x0 * MM, y0 * MM, W * MM, 40 * MM)
    c.setLineWidth(0.3 * MM)
    for y in (10, 20, 30):
        c.line(x0 * MM, (y0 + y) * MM, (x0 + W) * MM, (y0 + y) * MM)
    for x in (60, 130, 155):
        c.line((x0 + x) * MM, y0 * MM, (x0 + x) * MM, (y0 + 20) * MM)
    def t(x, y, s, txt, f='F'):
        c.setFont(f, s * MM)
        c.setFillColor(black)
        c.drawString((x0 + x) * MM, (y0 + y) * MM, txt)
    t(3, 33, 5, f'{TITLE}. Сборочный чертёж', 'FB')
    t(3, 23, 3.6, f'{CODE}   ·   ред. A   ·   {name}')
    t(3, 13, 3, f'Разраб.: {AUTHOR}')
    t(3, 3, 3, f'Дата: {date.today():%d.%m.%Y}')
    t(63, 13, 3, 'mso74.ru · kolman74@mso74.ru')
    t(63, 3, 3, 'Плата 240 × 127 мм, 4 слоя, 1,6 мм')
    t(133, 13, 3, 'Масштаб')
    t(133, 3, 4, scale, 'FB')
    t(158, 13, 3, 'Лист / листов')
    t(158, 3, 4, f'{sheet} / {total}', 'FB')


def legend(c, x, y):
    c.setFont('F', 3 * MM)
    items = [(RED, 'вывод 1 ИМС и разъёмов, катод диодов и светодиодов, «+» электролитических конденсаторов'),
             (PAD, 'контактные площадки'), (DNPC, 'не устанавливать (DNP), площадки свободны')]
    for i, (col, txt) in enumerate(items):
        c.setFillColor(col)
        c.setStrokeColor(Color(0.4, 0.4, 0.4))
        c.rect(x * MM, (y - i * 6) * MM, 5 * MM, 3.5 * MM, stroke=1, fill=1)
        c.setFillColor(black)
        c.drawString((x + 7) * MM, (y - i * 6 + 0.6) * MM, txt)


REQS = [
    'ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ',
    '1. Монтаж — только на верхней стороне платы (TOP). Нижняя сторона (BOTTOM) без компонентов.',
    '2. Комплектация — по спецификации «spec_mso74.xlsx» (позиции, парт-номера, коды LCSC). Замена ИМС, транзисторов',
    '    и разъёмов — только по согласованию с заказчиком; резисторы и керамические конденсаторы — аналог с теми же',
    '    номиналом, допуском, напряжением, ТКЕ и корпусом допускается.',
    '3. Ключи и полярность — по чертежу: красная площадка — вывод 1 микросхем, транзисторов и разъёмов, катод диодов',
    '    и светодиодов, вывод «+» электролитических конденсаторов. TVS-диоды с суффиксом CA неполярные.',
    '4. Не устанавливать (DNP, на чертеже синим, перечёркнуты): C81, R59, R60, J6, J17. Площадки оставить свободными.',
    '5. F1 — запаять только держатель Keystone 3568-10; вставку предохранителя не устанавливать.',
    '6. JP1 — запаять штыревую вилку; перемычку-джампер не устанавливать.',
    '7. TP1–TP21 — контрольные площадки, H1–H4 — крепёжные отверстия M3: монтажа нет.',
    '8. Центральные теплоотводящие площадки U1, U5, U6, U7, U8, U22, Q1 паять полностью (паста по трафарету).',
    '9. Выводные компоненты (клеммники, RJ45 J7/J18, J10, J14, F1, BT1, JP1) — корпус прижат к плате, без перекоса:',
    '    клеммники и разъёмы стоят у края платы и входят в вырезы корпуса изделия.',
    '10. Отмывка после монтажа — без ультразвука (кварцевые резонаторы Y1–Y3).',
    '11. Качество паяных соединений — по IPC-A-610, класс 2. Электростатически чувствительные изделия — соблюдать ESD-защиту.',
    '12. Координаты установки — файл pnp_mso74.csv: мм, начало — левый нижний угол платы, ось Y вверх, поворот — против',
    '    часовой стрелки (KiCad). При расхождении ориентации с этим чертежом руководствоваться чертежом.',
]


def main(board, out):
    font()
    b = parse(Path(board).read_text(encoding='utf-8'))
    parts = [Part(fp) for fp in findall(b, 'footprint')]
    edges = edges_of(b)
    xs = [q[0] for e in edges for q in e]
    ys = [q[1] for e in edges for q in e]
    bx0, by0, bw, bh = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    c = canvas.Canvas(out, pagesize=(A3[0] * MM, A3[1] * MM))
    c.setTitle(f'{TITLE} — сборочный чертёж')
    c.setAuthor('Кольман Павел')
    total = 6
    ov, ovx, ovy = 1.5, 20 + (395 - bw * 1.5) / 2, 18
    # четверти с перекрытием 4 мм
    hw, hh, ovl = bw / 2, bh / 2, 4
    quads = [('верх-лево', bx0, by0), ('верх-право', bx0 + hw - ovl, by0), ('низ-лево', bx0, by0 + hh - ovl),
             ('низ-право', bx0 + hw - ovl, by0 + hh - ovl)]
    # лист 1
    frame(c, 1, total, 'общий вид, сторона TOP', '1,5:1')
    Sheet(c, (bx0 - 1, by0 - 1, bw + 2, bh + 2), ov, ovx, ovy).board(edges, parts, 2.2, 0.7)
    s1 = Sheet(c, (bx0 - 1, by0 - 1, bw + 2, bh + 2), ov, ovx, ovy)
    c.setFont('FB', 4 * MM)
    c.setStrokeColor(DNPC)
    c.setLineWidth(0.3 * MM)
    c.setDash(3, 2)
    for i, (n, x, y) in enumerate(quads):
        (ax, ay), (bx2, by2) = s1.P(x, y), s1.P(x + hw + ovl, y + hh + ovl)
        c.rect(ax, by2, bx2 - ax, ay - by2)
    c.setDash()
    c.setFillColor(DNPC)
    for i, (n, x, y) in enumerate(quads):
        tx, ty = s1.P(x + 3 if i % 2 == 0 else x + hw + ovl - 3, y + 3 if i < 2 else y + hh + ovl - 3)
        (c.drawString if i % 2 == 0 else c.drawRightString)(tx, ty - (3 * MM if i < 2 else -1 * MM), f'лист {i + 3}')
    c.setFillColor(black)
    c.setFont('F', 3.2 * MM)
    c.drawString(25 * MM, 287 * MM, 'Вид сверху (TOP). Размеры платы 240 × 127 мм. Обозначения в увеличенном виде — листы 3–6.')
    legend(c, 25, 35)
    c.showPage()
    # лист 2
    frame(c, 2, total, 'технические требования', '—')
    y = 280
    for i, line in enumerate(REQS):
        c.setFont('FB' if i == 0 else 'F', (5 if i == 0 else 3.8) * MM)
        c.drawString(30 * MM, y * MM, line)
        y -= 9 if i == 0 else 6.2
    legend(c, 30, y - 10)
    c.showPage()
    # листы 3–6
    for i, (n, x, y) in enumerate(quads):
        frame(c, i + 3, total, f'фрагмент: {n}', '3:1')
        s = 3.0
        w, h = hw + ovl, hh + ovl
        Sheet(c, (x, y, w, h), s, 20 + (395 - w * s) / 2, 12).board(edges, parts, 3.5, 1.6)
        c.setFont('F', 3 * MM)
        c.setFillColor(black)
        c.drawString(25 * MM, 287.5 * MM, f'Фрагмент «{n}», вид сверху. Координаты окна X {x - bx0:.0f}…{x - bx0 + w:.0f} мм, '
                                         f'Y {y - by0:.0f}…{y - by0 + h:.0f} мм от левого верхнего угла платы. Перекрытие с соседними — 4 мм.')
        legend(c, 25, 35)
        c.showPage()
    c.save()
    print(out, 'деталей', len(parts))


if __name__ == '__main__':
    main(*sys.argv[1:3])
