"""Модуль табло МСО74 (свой шкаф, вклеенное стекло). Без сварки: П-обечайка и дно-корыто внутри неё, на винтах.
Матрица P4 64×32 на Z-скобах, DIN-рейка. PDF + DXF. Запуск: python3 modul_tablo.py <папка>  (рядом korpus_lib.py)

Толщина везде 1,5. Развёртки — по наружным размерам: внутренний радиус r = 2, K = 0,42
→ на гиб 90° длина дуги BA = 4,13, прямые участки = наружный размер − 3,5 у каждого гиба.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import korpus_lib  # noqa: E402
from korpus_lib import DIM, INK, MARKC, Part, Rectangle, dim, draw_part, part_block, plt, write_dxf  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

korpus_lib.VERSION = "Модуль табло v0.3 — черновик; развёртки уточнить пробным гибом"
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ металл и гиб
T = 1.5
RIN, K = 2.0, 0.42
BA = math.pi / 2 * (RIN + K * T)       # 4,13
SB = RIN + T                           # 3,5 — от наружной грани до начала дуги


def r2(v):
    return round(v, 2)


# ------------------------------------------------------------------ размеры (координаты лица: левый нижний угол)
FW, FH = 350, 220
CX, CY = FW / 2, FH / 2
MW, MH, MD = 256, 127, 19
MX0, MY0 = CX - MW / 2, CY - MH / 2
MHX, MHY = (12, 88, 165, 242), (12, 63, 114)
SW, SH, SD = 303, 173, 120            # обечайка снаружи, глубина от тыла лица
SX0, SY0 = CX - SW / 2, CY - SH / 2   # 23,5
FL_TOP, FL_SIDE, FL_TRAY = 12, 21, 12  # передние полки внутрь (от наружной грани стенки)
TRAY_W = SW - 2 * T - 0.5             # 299,5 — корыто внутри П с зазором 0,25 на герметик
TRAY_H = 30                           # борта корыта
TRAY_X0 = CX - TRAY_W / 2             # 25,25
GASK = 1.0                            # прокладка матрица — лицо
WEB_OUT = MW / 2 + 1 + T              # 130,5 — наружная грань стенки Z-скобы от оси
LEG_F, LEG_R = 15, 22
WEB = (GASK + MD + T) - T             # стенка Z (наружн.): от полки обечайки (глубина 1,5) до тыла полки за матрицей = 20
BR_L = 125
PEM_SIDE_X = (CX - WEB_OUT - LEG_F / 2, CX + WEB_OUT + LEG_F / 2)    # 37 / 313
PEM_SIDE_Y = (45, 70, 150, 180)       # 70 и 150 — общие со Z-скобами
PEM_TOP = [(x, SY0 + SH - 6.5) for x in (70, CX, 280)]
PEM_BOT = [(x, SY0 + 6.5) for x in (70, CX, 280)]
DOOR = [(12, 12), (CX, 12), (FW - 12, 12), (12, FH - 12), (CX, FH - 12), (FW - 12, FH - 12)]
RAIL_D = SD - 10
RAIL_Y = CY

parts = []

# ================================================================== T1. Лицо
p = Part("T1_lico", "Лицевая пластина табло", FW, FH, T, note=
         "Окно 258×129. 14 запрессовочных шпилек FH-M4-12 (отв. Ø4,2) — с лица заподлицо, закрыты металлом дверцы "
         "(проём 262×133). На них садятся передние полки П-обечайки и корыта, а на боковых — ещё и Z-скобы матрицы. "
         "6 отв. Ø5,5 — на шпильки дверцы. Сварки нет.")
p.rect(CX, CY, MW + 2, MH + 2, 1)
for x, y in DOOR: p.hole(x, y, 5.5)
for x in PEM_SIDE_X:
    for y in PEM_SIDE_Y: p.hole(x, y, 4.2)
for x, y in PEM_TOP + PEM_BOT: p.hole(x, y, 4.2)
x0, x1, y0, y1 = SX0, SX0 + SW, SY0, SY0 + SH
p.marks += [("line", x0, y0, x1, y0), ("line", x1, y0, x1, y1), ("line", x1, y1, x0, y1), ("line", x0, y1, x0, y0)]
parts.append(p)

# ================================================================== T2. Z-скоба ×2
zs = [LEG_F - SB, WEB - 2 * SB, LEG_R - SB]          # прямые участки
ZW = sum(zs) + 2 * BA
p = Part("T2_skoba_matricy", "Z-скоба матрицы (развёртка)", r2(ZW), BR_L, T, qty=2, note=
         f"Наружные: полка {LEG_F} / стенка {WEB:g} / полка {LEG_R}, гибы в разные стороны. Полка {LEG_F} — на боковую "
         "полку обечайки, на те же шпильки M4 (пазы — подвижка ±1,75). Полка 22 — за матрицей, 3 отв. Ø3,4 под M3 "
         "в её крайний ряд. Вторая скоба — зеркально.")
yb = CY - BR_L / 2
for y in (70, 150): p.rect(LEG_F - LEG_F / 2, y - yb, 4.5, 8, 2.25)
hx = zs[0] + BA + zs[1] + BA + (WEB_OUT - (MW / 2 - MHX[0]) - SB)
for y in MHY: p.hole(r2(hx), MY0 + y - yb, 3.4)
b1 = zs[0] + BA / 2; b2 = zs[0] + BA + zs[1] + BA / 2
p.marks += [("line", r2(b1), 0, r2(b1), BR_L), ("line", r2(b2), 0, r2(b2), BR_L)]
parts.append(p)

# ================================================================== T3. П-обечайка (верх + 2 боковины), одна деталь
side_st = SH - SB                     # прямой участок боковины (от свободного низа до дуги)
top_st = SW - 2 * SB
L = 2 * side_st + top_st + 2 * BA     # 643,26
Y_FB = SD - SB                        # начало дуги передней полки от заднего края (116,5)


def yd(d):                            # глубина от тыла лица → Y развёртки (Y = 0 — задний край)
    return SD - d


def yw(w):                            # полка: расстояние от наружной грани стенки → Y
    return Y_FB + BA + (w - SB)


def x_side1(h): return h                                      # высота от низа боковины
def x_top(u): return side_st + BA + (u - SB)                  # от наружной грани левой боковины
def x_side2(h): return L - h


NOTCH_Y = Y_FB - 0.5
s_end = (SH - T - RIN - 1)                                    # 168,5
t_beg = x_top(FL_SIDE)                                        # верхняя полка начинается за боковой полкой
p = Part("T3_obechayka_P", "П-обечайка: верх + боковины (развёртка)", r2(L), r2(yw(FL_SIDE)), T, note=
         f"Одна деталь, 3 гиба 90° внутрь. Наружные: боковины {SH} / верх {SW} / боковины {SH}, глубина {SD}. "
         f"Передняя полка внутрь: на верхе {FL_TOP}, на боковинах {FL_SIDE} (на них же Z-скобы). Порядок: сначала "
         "передняя полка (длинный гиб), затем 2 угла. Ø4,5 у низа боковин — винты в корыто; Ø6 у заднего края — "
         "резьбовые заклёпки M4 под крышку (ставятся снаружи, бортик Ø≈9 входит в отв. Ø10 борта крышки); Ø4,5 в середине боковин — уголки DIN.")
YS, YT = r2(yw(FL_SIDE)), r2(yw(FL_TOP))
p.poly = [(0, 0), (r2(L), 0), (r2(L), YS), (r2(L - s_end), YS), (r2(L - s_end), r2(NOTCH_Y)), (r2(L - t_beg), r2(NOTCH_Y)),
          (r2(L - t_beg), YT), (r2(t_beg), YT), (r2(t_beg), r2(NOTCH_Y)), (r2(s_end), r2(NOTCH_Y)), (r2(s_end), YS), (0, YS)]
for xb in (side_st + BA / 2, L - side_st - BA / 2):
    p.marks.append(("line", r2(xb), 0, r2(xb), r2(NOTCH_Y)))
yfb = r2(Y_FB + BA / 2)
p.marks += [("line", 0, yfb, r2(s_end), yfb), ("line", r2(t_beg), yfb, r2(L - t_beg), yfb), ("line", r2(L - s_end), yfb, r2(L), yfb)]
# полки → шпильки лица
w_side = PEM_SIDE_X[0] - SX0                                   # 13,5
for y in PEM_SIDE_Y:
    p.hole(x_side1(y - SY0), r2(yw(w_side)), 4.5); p.hole(r2(x_side2(y - SY0)), r2(yw(w_side)), 4.5)
for x, y in PEM_TOP:
    p.hole(r2(x_top(x - SX0)), r2(yw(SY0 + SH - y)), 4.5)
# задний край → крышка
for u in (40, SW / 2, SW - 40): p.hole(r2(x_top(u)), yd(SD - 10), 6)
for h in (55, 125):
    p.hole(x_side1(h), yd(SD - 10), 6); p.hole(r2(x_side2(h)), yd(SD - 10), 6)
# низ боковин → корыто (винт M4 снаружи, гайка M4 с шайбой изнутри)
for d in (30, 90):
    p.hole(x_side1(15), yd(d), 4.5); p.hole(r2(x_side2(15)), yd(d), 4.5)
# уголки DIN
hr = RAIL_Y - SY0
for dh in (-12, 12):
    p.hole(x_side1(hr + dh), yd(RAIL_D - 12.5), 4.5); p.hole(r2(x_side2(hr + dh)), yd(RAIL_D - 12.5), 4.5)
parts.append(p)

# ================================================================== T4. Дно-корыто (внутри П)
tf_st = TRAY_H - SB
tb_st = TRAY_W - 2 * SB
TWF = 2 * tf_st + tb_st + 2 * BA      # 353,76
fr_beg = (SX0 + FL_SIDE + 0.5) - TRAY_X0                      # 19,75 от наружной грани борта


def tx(u): return tf_st + BA + (u - SB)                       # от наружной грани левого борта
def tx_fl(h): return TRAY_H - h                               # борт: высота над наружным дном → X (левый)


SIDE_STOP = yd(2)                                             # борта не доходят до лица 2 мм (там полка П)
p = Part("T4_dno_koryto", "Дно-корыто (развёртка)", r2(TWF), r2(yw(FL_TRAY)), T, note=
         f"Вкладывается внутрь П: наружная ширина {TRAY_W:g} (зазор 0,25 на сторону под герметик), борта {TRAY_H} вверх, "
         f"передняя полка {FL_TRAY} вверх — на шпильки лица. Борта прижаты к боковинам изнутри: по 2 винта M4 "
         "(отв. Ø4,5) на сторону, гайка с шайбой изнутри корыта, шов на герметике. Боковины снаружи перекрывают борта — вода не "
         "затекает. Вводы: Ø32,5 — M32 разрезной под шлейф HUB75; Ø20,5 — M20 питание 24 В; Ø12,5 — клапан M12.")
YF = r2(yw(FL_TRAY))
xf0 = r2(tx(fr_beg))
p.poly = [(0, 0), (r2(TWF), 0), (r2(TWF), r2(SIDE_STOP)), (r2(TWF - tf_st), r2(SIDE_STOP)), (r2(TWF - tf_st), r2(NOTCH_Y)),
          (r2(TWF - xf0), r2(NOTCH_Y)), (r2(TWF - xf0), YF), (xf0, YF), (xf0, r2(NOTCH_Y)), (r2(tf_st), r2(NOTCH_Y)),
          (r2(tf_st), r2(SIDE_STOP)), (0, r2(SIDE_STOP))]
for xb in (tf_st + BA / 2, TWF - tf_st - BA / 2):
    p.marks.append(("line", r2(xb), 0, r2(xb), r2(NOTCH_Y)))
p.marks.append(("line", xf0, yfb, r2(TWF - xf0), yfb))
for x, y in PEM_BOT: p.hole(r2(tx(x - TRAY_X0)), r2(yw(y - SY0)), 4.5)
for d in (30, 90):
    p.hole(tx_fl(15), yd(d), 4.5); p.hole(r2(TWF - tx_fl(15)), yd(d), 4.5)
for u in (40, SW / 2, SW - 40): p.hole(r2(tx(u - (TRAY_X0 - SX0))), yd(SD - 10), 6)
p.hole(r2(tx(90 - TRAY_X0)), yd(65), 32.5); p.hole(r2(tx(160 - TRAY_X0)), yd(65), 20.5); p.hole(r2(tx(250 - TRAY_X0)), yd(80), 12.5)
parts.append(p)

# ================================================================== T5. Уголок DIN ×2
p = Part("T5_ugolok_din", "Уголок DIN-рейки (развёртка)", r2(25 - SB + BA + 30 - SB), 40, T, qty=2, note=
         "Наружные полки 25 и 30. Полка 25 — к боковине 2 винтами M4 с гайками (отв. Ø4,5, шаг 24), полка 30 — "
         "рейка 35 мм длиной 290, винт M4 + гайка.")
xb = 25 - SB + BA / 2
p.marks.append(("line", r2(xb), 0, r2(xb), 40))
for y in (8, 32): p.hole(12.5, y, 4.5)
p.hole(r2(25 - SB + BA + (30 - 12) - SB), 20, 4.5)
parts.append(p)

# ================================================================== T6. Крышка-короб (борта вперёд, снаружи обечайки)
LC = 0.25                                  # зазор крышка — обечайка на сторону
LF = 20                                    # наружная высота борта
LOW, LOH = SW + 2 * LC + 2 * T, SH + 2 * LC + 2 * T     # наружные размеры крышки 306,5 × 176,5
lf_st = LF - SB
BW, BH = r2(LOW - 2 * SB + 2 * (BA + lf_st)), r2(LOH - 2 * SB + 2 * (BA + lf_st))
C = r2(lf_st + BA)                         # вырубка углов
OFF = LC + T                               # наружная грань крышки от наружной грани обечайки
HOLE_FROM_EDGE = LF - (T + 10)            # отв. в борту: 10 от заднего края обечайки → от кромки борта


def lx(u): return C + (u + OFF - SB)       # вдоль ширины, вид спереди
def ly(h): return C + (h + OFF - SB)       # вдоль высоты


p = Part("T6_kryshka", "Задняя крышка-короб (развёртка, вид снаружи)", BW, BH, T, note=
         f"Наружные {LOW:g}×{LOH:g}, борта {LF} загибаются ВПЕРЁД (к лицу) по 4 сторонам, углы вырублены. Крышка надевается "
         f"на задний край обечайки снаружи (зазор {LC} на сторону, на верх/низ — так же), упирается дном в торец обечайки. "
         "10 винтов M4×10 с широкой шайбой (DIN 9021, Ø12) в резьбовые заклёпки обечайки и корыта (10 от заднего края); "
         "отв. в бортах Ø10 — в них входит бортик заклёпки, борт крышки ложится на стенку без зазора. "
         "Под дно крышки — уплотнитель 3×10 по торцу обечайки. Вид снаружи: лево/право зеркально виду спереди.")
p.poly = [(C, 0), (BW - C, 0), (BW - C, C), (BW, C), (BW, BH - C), (BW - C, BH - C), (BW - C, BH),
          (C, BH), (C, BH - C), (0, BH - C), (0, C), (C, C)]
bl = r2(lf_st + BA / 2)
p.marks += [("line", C, bl, BW - C, bl), ("line", C, BH - bl, BW - C, BH - bl),
            ("line", bl, C, bl, BH - C), ("line", BW - bl, C, BW - bl, BH - C)]
for u in (40, SW / 2, SW - 40):
    x = r2(BW - lx(u))
    p.hole(x, HOLE_FROM_EDGE, 10); p.hole(x, r2(BH - HOLE_FROM_EDGE), 10)
for h in (55, 125):
    p.hole(HOLE_FROM_EDGE, r2(ly(h)), 10); p.hole(r2(BW - HOLE_FROM_EDGE), r2(ly(h)), 10)
# табло кассы и сервисная кнопка — по центру по ширине, внизу: за серединой крышки стоит DIN-рейка
SVC_H = 28                                 # ось по высоте от низа обечайки (ниже модулей на рейке, h < 41,5)
sy = r2(ly(SVC_H)); dx_ = r2(BW / 2 - 35); bx_ = r2(BW / 2 + 40)
p.rect(dx_, sy, 58, 26, 1)
p.hole(bx_, sy, 16)
p.text(dx_, r2(sy + 19), 4, "КАССА")
p.text(bx_, r2(sy + 21), 3.5, "НАЖАТЬ — НАСТРОЙКИ")
p.text(bx_, r2(sy + 14), 3.5, "УДЕРЖИВАТЬ — ИНКАССАЦИЯ")
p.note += (" Табло кассы — вырез 58×26, сервисная кнопка — Ø16, гравировка (слой ENGRAVE): «КАССА», «НАЖАТЬ — НАСТРОЙКИ», "
           "«УДЕРЖИВАТЬ — ИНКАССАЦИЯ». Стоят внизу по центру: за серединой крышки DIN-рейка, табло (19) и кнопка (20) в неё упрутся.")
parts.append(p)

# ================================================================== T7. Шаблон дверцы
p = Part("T7_dverca_zona_tablo", "Дверца в зоне табло: проём и шпильки", FW, FH, T, note=
         "Не деталь — шаблон для чертежа дверцы. Проём 262×133 R3, стекло перед ним сплошное. 6 шпилек M5 приварить "
         "до вклейки стекла.")
p.rect(CX, CY, 262, 133, 3)
for x, y in DOOR: p.stud(x, y)
parts.append(p)

for p in parts:
    write_dxf(p, os.path.join(OUT, p.key + ".dxf"))


# ================================================================== рисунки
def R(ax, x, y, w, h, fc="none", ec=INK, lw=0.9, ls="-", z=3, a=1.0):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, ls=ls, zorder=z, alpha=a))


STEEL, DARK, GLASS, RAIL, TRAYC = "#b9c0c7", "#15191e", "#9fd3e6", "#8a939c", "#7fa7c9"
DIN_MODS = [("FU\n24 В", 18, 80, 60), ("клеммы\n24 В", 30, 45, 45), ("DC-DC\n24→5 В\nна DIN\n≥ 6 А", 72, 90, 60), ("клеммы\n5 В", 30, 45, 45)]


def lab(ax, xy, t, xt, c=INK):
    ax.annotate(t, xy=xy, xytext=xt, fontsize=7.6, color=c, zorder=20, va="center",
                arrowprops=dict(arrowstyle="-", color="#6b7580", lw=0.7))


def front_view(ax):
    draw_part(ax, parts[0])
    R(ax, MX0, MY0, MW, MH, fc=DARK, z=3.5)
    ax.text(CX, CY, "матрица P4 64×32\n256×127×19", color="#3fd7b6", ha="center", va="center", fontsize=9, zorder=6)
    # полки П и корыта за лицом
    for x in (SX0, SX0 + SW - FL_SIDE):
        R(ax, x, SY0, FL_SIDE, SH, ec=TRAYC, ls="--", lw=0.8, z=4)
    R(ax, SX0 + FL_SIDE, SY0 + SH - FL_TOP, SW - 2 * FL_SIDE, FL_TOP, ec=TRAYC, ls="--", lw=0.8, z=4)
    R(ax, TRAY_X0 + fr_beg, SY0, TRAY_W - 2 * fr_beg, FL_TRAY, ec=TRAYC, ls="--", lw=0.8, z=4)
    for s in (-1, 1):
        x = CX + s * WEB_OUT + (0 if s > 0 else -LEG_F)
        R(ax, x, CY - BR_L / 2, LEG_F, BR_L, ec=MARKC, ls="--", lw=0.9, z=4.5)
    dim(ax, (0, 0), (FW, 0), -18); dim(ax, (0, 0), (0, FH), -18)
    dim(ax, (MX0 - 1, FH), (MX0 + MW + 1, FH), 10, "окно 258×129")
    dim(ax, (SX0, SY0), (SX0 + SW, SY0), -32, "обечайка 303 (наружн.)", fs=6.5)
    ax.set_xlim(-35, FW + 15); ax.set_ylim(-55, FH + 25)
    ax.set_title("Вид спереди. Пунктир: синий — полки обечайки и корыта, красный — полки Z-скоб", fontsize=9.5,
                 color=INK, fontweight="bold", loc="left")


def section_geom(ax, detail=False):
    x0, y0 = SX0, SY0
    W = "#5b6670"
    R(ax, x0, y0, T, SH, fc=W, ec="none", z=4); R(ax, x0 + SW - T, y0, T, SH, fc=W, ec="none", z=4)
    R(ax, x0, y0 + SH - T, SW, T, fc=W, ec="none", z=4)
    tx0 = TRAY_X0
    R(ax, tx0, y0, TRAY_W, T, fc=TRAYC, ec="none", z=5)
    R(ax, tx0, y0, T, TRAY_H, fc=TRAYC, ec="none", z=5); R(ax, tx0 + TRAY_W - T, y0, T, TRAY_H, fc=TRAYC, ec="none", z=5)
    for side in (-1, 1):
        xo = x0 if side < 0 else x0 + SW                       # наружная грань стенки
        xi = tx0 + T if side < 0 else tx0 + TRAY_W - T          # внутренняя грань борта
        sgn = -side
        # винт M4: головка снаружи, стержень сквозь стенку и борт, гайка с шайбой изнутри
        R(ax, min(xo, xo - side * 2.8), y0 + 15 - 3.5, 2.8, 7, fc="#2b3138", ec="none", z=7)
        R(ax, min(xo, xi + sgn * 6), y0 + 15 - 2, abs(xi + sgn * 6 - xo), 4, fc="#2b3138", ec="none", z=6)
        R(ax, min(xi, xi + sgn * 6), y0 + 15 - 3, 6, 6, fc="#8a6d3b", ec="none", z=6.5)   # тело гайки внутри
        if detail:
            R(ax, (tx0 - 0.25) if side < 0 else tx0 + TRAY_W, y0 + 1, 0.25, TRAY_H - 1, fc="#e0a33a", ec="none", z=6)
    if detail:
        lab(ax, (x0 + 0.75, y0 + 36), "стенка П 1,5 (снаружи)", (x0 + 6, y0 + 41))
        lab(ax, (x0 + 2.4, y0 + 28.5), "борт корыта 1,5", (x0 + 9, y0 + 34))
        ax.text(x0 + 12, y0 + 2.5, "дно корыта 1,5", fontsize=7, color=INK, va="bottom")
        ax.text(x0 + 9, y0 + 19.5, "гайка M4\n+ шайба", fontsize=6.5, color=INK, va="bottom")
        lab(ax, (x0 - 1.5, y0 + 15), "винт M4", (x0 - 11, y0 + 24))
        ax.text(x0 + 9, y0 + 25, "герметик (зазор 0,25)", fontsize=6.5, color="#b07a12", va="center")
        dim(ax, (x0, y0), (x0, y0 + TRAY_H), -7, "30", fs=6.5)
        dim(ax, (x0, y0 - 1), (x0 + T, y0 - 1), -3, "1,5", fs=6)
        ax.annotate("вода стекает по стенке\nмимо шва (стенка снаружи)", xy=(x0 - 0.8, y0 - 0.5), xytext=(x0 + 8, y0 - 8),
                    fontsize=6.5, color=INK, arrowprops=dict(arrowstyle="->", color="#2b6cb0", lw=0.8))


def cross_section(ax):
    """Поперечное сечение обечайки (вид сзади, крышка снята)."""
    x0, y0 = SX0, SY0
    section_geom(ax)
    R(ax, x0 - 4, y0 - 4, 40, 44, ec=MARKC, ls="--", lw=0.8, z=8)
    ax.text(x0 + 38, y0 + 42, "А", fontsize=10, color=MARKC, fontweight="bold")
    dim(ax, (x0, y0 + SH), (x0 + SW, y0 + SH), 12, "303 наружн.")
    dim(ax, (x0 + T, y0 + SH - T), (x0 + SW - T, y0 + SH - T), -12, "300 внутр.", fs=6.5)
    dim(ax, (TRAY_X0 + T, y0 + TRAY_H), (TRAY_X0 + TRAY_W - T, y0 + TRAY_H), 8, f"{TRAY_W - 2 * T:g} между бортами", fs=6.5)
    dim(ax, (x0 + SW, y0), (x0 + SW, y0 + SH), 14, "173 наружн.")
    dim(ax, (x0 + SW - T, y0 + T), (x0 + SW - T, y0 + SH - T), -12, "170 внутр.", fs=6.5)
    ax.text(x0 + SW / 2, y0 + SH / 2 + 10, "П-обечайка — одна деталь, 2 гиба\n(передняя полка — третий гиб)",
            fontsize=7.5, ha="center", color=INK)
    ax.text(x0 + SW / 2, y0 + 62, "корыто — внутри П, борта 30", fontsize=7.5, ha="center", color="#2f5f8a")
    ax.set_xlim(x0 - 8, x0 + SW + 30); ax.set_ylim(y0 - 10, y0 + SH + 25); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Сечение обечайки (вид сзади)", fontsize=9.5, color=INK, fontweight="bold", loc="left")


def lid_detail(ax):
    """Узел Б: разрез по верху у заднего края, сбоку. z — глубина вправо, y — высота."""
    W = "#5b6670"
    z0 = SD                                   # задний торец обечайки (от тыла лица)
    yt = SH                                   # наружная грань верха (от низа обечайки)
    R(ax, z0 - 40, yt - T, 40, T, fc=W, ec="none", z=4)                       # верх обечайки
    R(ax, z0, yt - 40, 3, 40 + LC + T, fc="#2f3338", ec="none", z=3)          # уплотнитель по торцу (условно)
    R(ax, z0 + 3, yt - 40, T, 40 + LC + T, fc="#c0392b", ec="none", z=4)      # дно крышки
    R(ax, z0 + 3 + T - LF, yt + LC, LF - T, T, fc="#c0392b", ec="none", z=4)   # борт крышки вперёд
    R(ax, z0 - 10 - 5, yt + LC + T - 0.01, 10, 0.02, fc="white", ec="none", z=4.5)   # (условно)
    R(ax, z0 - 10 - 5, yt + LC, 10, T, fc="white", ec="none", z=4.6)         # отв. Ø10 в борту крышки
    R(ax, z0 - 10 - 4.5, yt, 9, 0.8, fc="#6b5228", ec="none", z=5.5)          # бортик заклёпки снаружи, в отверстии
    R(ax, z0 - 10 - 3, yt - T - 6, 6, 6 + T, fc="#8a6d3b", ec="none", z=5)    # тело заклёпки внутри
    R(ax, z0 - 10 - 2, yt - T - 8, 4, 8 + T + LC + T, fc="#2b3138", ec="none", z=6)   # винт
    R(ax, z0 - 10 - 6, yt + LC + T, 12, 1, fc="#9aa2ab", ec="none", z=6)     # шайба Ø12
    R(ax, z0 - 10 - 3.5, yt + LC + T + 1, 7, 2.8, fc="#2b3138", ec="none", z=6)  # головка
    ax.text(z0 - 38, yt - T - 3, "верх П-обечайки 1,5", fontsize=7, color=INK, va="top")
    ax.text(z0 + 6.5, yt - 20, "дно крышки 1,5", fontsize=7, color="#c0392b", rotation=90, va="center")
    ax.text(z0 + 0.5, yt - 30, "уплотнитель", fontsize=6.5, color="white", rotation=90, va="center", ha="left")
    lab(ax, (z0 - 4, yt + LC + T / 2 + 0.2), f"борт крышки {LF} — вперёд,\nповерх обечайки (зазор {LC})", (z0 - 40, yt + 14))
    lab(ax, (z0 - 10, yt + LC + T + 2.5), "винт M4×10 + шайба Ø12", (z0 - 40, yt + 22))
    lab(ax, (z0 - 10, yt - T - 3), "резьбовая заклёпка M4 (отв. Ø6),\nбортик снаружи — входит\nв отв. Ø10 борта крышки", (z0 - 40, yt - 16))
    dim(ax, (z0 - 10, yt + 6), (z0, yt + 6), 4, "10", fs=6.5)
    dim(ax, (z0 + 3 + T - LF, yt + LC + T), (z0 + 3 + T, yt + LC + T), 9, f"{LF}", fs=6.5)
    ax.annotate("", xy=(z0 + 10, yt - 34), xytext=(z0 + 24, yt - 34), arrowprops=dict(arrowstyle="->", color=INK, lw=1))
    ax.text(z0 + 25, yt - 34, "надевается\nвперёд", fontsize=7, va="center", color=INK)
    ax.set_xlim(z0 - 42, z0 + 40); ax.set_ylim(yt - 42, yt + 28); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Узел Б (крупно): крышка на заднем крае, разрез по верху", fontsize=10, color=MARKC, fontweight="bold", loc="left")


def lid_side(ax):
    """Вид сбоку модуля: крышка снята и сдвинута назад."""
    W = "#5b6670"
    R(ax, -T, -SY0, T, FH, fc="#d9dde1", z=3)                                  # лицо (y от низа обечайки)
    R(ax, 0, 0, SD, SH, fc="#eef1f4", ec=W, lw=1.2, z=2)                        # боковина П
    R(ax, 0, 0, SD, TRAY_H, fc="none", ec=TRAYC, ls="--", lw=0.9, z=3)          # борт корыта за боковиной
    for h in (55, 125): ax.add_patch(plt.Circle((SD - 10, h), 2.3, fc="white", ec=INK, lw=0.8, zorder=4))
    for d in (30, 90): ax.add_patch(plt.Circle((d, 15), 2.0, fc="white", ec=INK, lw=0.8, zorder=4))
    ax.text(SD - 10, 72, "заклёпки\nM4", fontsize=6.5, ha="center", color=INK)
    gap = 45
    zl = SD + gap
    R(ax, zl + LF - T, -LC - T, T, LOH, fc="#f3c7c2", ec="#c0392b", z=3)         # дно крышки (торцом)
    R(ax, zl, -LC - T, LF, LOH, fc="#f3c7c2", ec="#c0392b", lw=1, z=2.5)          # боковой борт (виден)
    for h in (55, 125): ax.add_patch(plt.Circle((zl + LF - T - 10, h), 5, fc="white", ec=INK, lw=0.8, zorder=4))
    ax.annotate("", xy=(SD + 4, SH / 2), xytext=(zl - 4, SH / 2), arrowprops=dict(arrowstyle="->", color=INK, lw=1.2))
    ax.text(SD + gap / 2, SH / 2 + 6, "крышка\nнадевается", fontsize=7.5, ha="center", color=INK)
    ax.text(SD / 2, SH + 6, "боковина П-обечайки", fontsize=7.5, ha="center", color=INK)
    ax.text(zl + LF / 2, SH + 6, "крышка", fontsize=7.5, ha="center", color="#c0392b")
    ax.text(SD / 2, TRAY_H + 3, "борт корыта (за стенкой)", fontsize=6.5, ha="center", color="#2f5f8a")
    dim(ax, (0, -12), (SD, -12), -6, f"{SD}")
    dim(ax, (zl, -LC - T), (zl + LF, -LC - T), -10, f"{LF}", fs=6.5)
    ax.set_xlim(-15, zl + LF + 25); ax.set_ylim(-35, SH + 20); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Вид сбоку: крышка снята", fontsize=10, color=INK, fontweight="bold", loc="left")


def detail_a(ax):
    section_geom(ax, detail=True)
    ax.set_xlim(SX0 - 12, SX0 + 30); ax.set_ylim(SY0 - 12, SY0 + 45); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Узел А (крупно): шов корыта", fontsize=9.5, color=MARKC, fontweight="bold", loc="left")


def top_section(ax):
    """Горизонтальный разрез по оси табло; глубина вниз."""
    D = lambda d: -d   # noqa: E731
    R(ax, -20, 5.5, FW + 40, 4, fc=GLASS, ec="#5b8fa3", a=0.6, z=2)
    for a0, a1 in ((-20, CX - 131), (CX + 131, FW + 20)): R(ax, a0, 4, a1 - a0, 1.5, fc="#9aa2ab", z=2)
    R(ax, 0, 1, FW, 3, fc="#2f3338", ec="none", z=2)
    R(ax, 0, D(T), FW, T, fc="#d9dde1", z=4)                                           # лицо
    R(ax, MX0, D(T + GASK + MD), MW, MD, fc=DARK, z=4)
    for s in (-1, 1):
        wall = SX0 if s < 0 else SX0 + SW - T
        R(ax, wall, D(T + SD), T, SD, fc=STEEL, ec="none", z=4)                       # стенка П
        fx = SX0 if s < 0 else SX0 + SW - FL_SIDE
        R(ax, fx, D(2 * T), FL_SIDE, T, fc=STEEL, ec="none", z=4)                     # полка П
        wo = CX + s * WEB_OUT
        wx = wo if s < 0 else wo - T
        R(ax, wx, D(2 * T + WEB - T), T, WEB, fc=MARKC, ec="none", z=5)               # стенка Z
        lx = wo - LEG_F if s < 0 else wo
        R(ax, lx, D(3 * T), LEG_F, T, fc=MARKC, ec="none", z=5)                       # полка Z на полке П
        rx = wo if s < 0 else wo - LEG_R
        R(ax, rx, D(T + GASK + MD + T), LEG_R, T, fc=MARKC, ec="none", z=5)           # полка за матрицей
        sx = CX + s * (WEB_OUT + LEG_F / 2)
        R(ax, sx - 2, D(T + 10), 4, 10, fc="#4a5560", ec="none", z=6)
        R(ax, sx - 3.5, D(3 * T + 3), 7, 3, fc="#4a5560", ec="none", z=6)
        hx = CX + s * (MW / 2 - MHX[0])
        R(ax, hx - 1.5, D(T + GASK + MD + T + 4), 3, 10, fc="#4a5560", ec="none", z=6)
    R(ax, SX0 - T, D(T + SD + T), SW + 2 * T, T, fc=STEEL, ec="none", z=4)
    R(ax, SX0 + T, D(T + RAIL_D), SW - 2 * T, 7.5, fc=RAIL, z=4)
    x = SX0 + 10
    for name, w, h, d in DIN_MODS:
        R(ax, x, D(T + RAIL_D), w, d, fc="#e9ecef", z=4.5); x += w + 3
    lab(ax, (CX + WEB_OUT - 0.7, D(12)), "Z-скоба: полка на полке\nобечайки, общая шпилька", (SX0 + SW + 8, D(20)), MARKC)
    lab(ax, (CX + MW / 2 - 12, D(T + GASK + MD + 8)), "винт M3 в матрицу", (SX0 + SW + 8, D(48)))
    lab(ax, (CX + 60, D(T + GASK + 3)), "прокладка 1 мм", (SX0 + SW + 8, D(66)))
    lab(ax, (SX0 + SW - 20, D(T + RAIL_D - 30)), "модули на DIN", (SX0 + SW + 8, D(88)))
    ax.text(-18, 12, "стекло, дверца", fontsize=7.5, color=INK)
    dim(ax, (-5, D(0)), (-5, D(T + SD + T)), -12, f"{T + SD + T:g}")
    ax.set_xlim(-30, FW + 85); ax.set_ylim(D(T + SD + 15), 25); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Разрез сверху по оси табло (стекло вверху)", fontsize=9.5, color=INK, fontweight="bold", loc="left")


def rear_view(ax):
    R(ax, -10, -10, SW + 20, SH + 20, fc="#eef1f4", ec=INK, z=1)
    R(ax, 0, 0, SW, SH, fc="white", ec=INK, lw=1.2, z=2); R(ax, T, T, SW - 2 * T, SH - 2 * T, fc="#f7f8f9", ec=INK, lw=0.6, z=2)
    tx0 = TRAY_X0 - SX0
    R(ax, tx0, 0, TRAY_W, T, fc=TRAYC, ec="none", z=2.5); R(ax, tx0, 0, T, TRAY_H, fc=TRAYC, ec="none", z=2.5)
    R(ax, tx0 + TRAY_W - T, 0, T, TRAY_H, fc=TRAYC, ec="none", z=2.5)
    mx0, my0 = SW / 2 - MW / 2, SH / 2 - MH / 2
    R(ax, mx0, my0, MW, MH, fc="#2b3138", z=3)
    ax.text(mx0 + 30, my0 + MH - 10, "тыл матрицы", fontsize=7, color="#cfd4d9", va="center", zorder=4)
    for s in (-1, 1):
        xx = SW / 2 + WEB_OUT - LEG_R if s > 0 else SW / 2 - WEB_OUT
        R(ax, xx, SH / 2 - BR_L / 2, LEG_R, BR_L, fc="#e3a6a0", ec=MARKC, z=4)
        hx = SW / 2 + s * (MW / 2 - MHX[0])
        for y in MHY:
            ax.add_patch(plt.Circle((hx, my0 + y), 2.2, fc="#5b646d", ec="none", zorder=5))
        R(ax, (T if s < 0 else SW - T - 25), SH / 2 - 20, 25, 40, fc="#9aa2ab", z=5)
    R(ax, T, SH / 2 - 17.5, SW - 2 * T, 35, fc=RAIL, z=6)
    x = 32
    for name, w, h, d in DIN_MODS:
        R(ax, x, SH / 2 - h / 2, w, h, fc="#e9ecef", ec=INK, z=8)
        ax.text(x + w / 2, SH / 2, name, fontsize=6.3, ha="center", va="center", color=INK, zorder=9, linespacing=1.15)
        x += w + 3
    lab(ax, (SW - 30, SH / 2 + 12), "DIN-рейка 35 мм, 290 — на уголках,\nкаждый 2 винтами M4 к боковине", (SW + 15, SH / 2 + 60))
    lab(ax, (mx0 + 14, my0 + 20), "полки Z-скоб, винты M3\nв крайние ряды матрицы", (SW + 15, my0 + 5))
    lab(ax, (60, 1), "дно-корыто: вводы M32 (HUB75),\nM20 (24 В), клапан M12", (SW + 15, -12))
    ax.set_xlim(-25, SW + 160); ax.set_ylim(-35, SH + 20); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Вид сзади без крышки", fontsize=9.5, color=INK, fontweight="bold", loc="left")


pdf_path = os.path.join(OUT, "modul_tablo.pdf")
with PdfPages(pdf_path) as pdf:
    fig = korpus_lib.sheet(pdf, "Модуль табло: сборка", 1)
    ax = fig.add_axes([0.01, 0.52, 0.40, 0.42]); ax.set_aspect("equal"); ax.axis("off"); front_view(ax)
    top_section(fig.add_axes([0.42, 0.52, 0.57, 0.42]))
    cross_section(fig.add_axes([0.01, 0.06, 0.24, 0.40])); detail_a(fig.add_axes([0.25, 0.05, 0.18, 0.46]))
    rear_view(fig.add_axes([0.44, 0.06, 0.36, 0.40]))
    ax = fig.add_axes([0.80, 0.06, 0.19, 0.42]); ax.axis("off")
    notes = [
        "Без сварки",
        "• П-обечайка — одна деталь:",
        "  передняя полка, потом 2 угла.",
        "• Корыто — внутри П, 2+2 винта",
        "  M4 + герметик. Боковины",
        "  перекрывают борта снаружи.",
        "• Всё на 14 шпильках лица:",
        "  полки П, корыта и Z-скобы.",
        "",
        "Толщина 1,5 учтена:",
        "наружн. 303×173, внутри",
        "300×170, между бортами",
        "корыта 296,5. Развёртки:",
        "r = 2, K = 0,42 (BA 4,13) —",
        "уточнить пробным гибом.",
        "",
        "Детали: T1 лицо · T2 Z-скоба ×2",
        "T3 П-обечайка · T4 корыто",
        "T5 уголок DIN ×2 · T6 крышка",
        "T7 шаблон дверцы",
    ]
    ax.text(0, 1, "\n".join(notes), fontsize=8.2, color=INK, va="top", transform=ax.transAxes, linespacing=1.45)
    pdf.savefig(fig); fig.savefig(os.path.join(OUT, "sborka.png"), dpi=110); plt.close(fig)

    def page(title, num, blocks):
        fig = korpus_lib.sheet(pdf, title, num)
        for rc, key in blocks:
            part_block(fig, rc, next(q for q in parts if q.key.startswith(key)))
        pdf.savefig(fig); plt.close(fig)

    fig = korpus_lib.sheet(pdf, "Модуль табло: задняя крышка — как крепится", 2)
    lid_side(fig.add_axes([0.02, 0.50, 0.50, 0.42])); lid_detail(fig.add_axes([0.52, 0.47, 0.46, 0.46]))
    part_block(fig, [0.02, 0.05, 0.60, 0.38], next(q for q in parts if q.key.startswith("T6")))
    ax = fig.add_axes([0.64, 0.06, 0.34, 0.36]); ax.axis("off")
    ax.text(0, 1, "\n".join([
        "Крышка — короб из одного листа:",
        "• дно 306,5×176,5 и 4 борта по 20, загнуты ВПЕРЁД;",
        "• углы вырублены — борта не мешают друг другу;",
        "• надевается на задний край обечайки снаружи,",
        "  упирается дном в торец через уплотнитель;",
        "• 10 винтов M4 через борта: верх 3, низ 3 (в дно",
        "  корыта), бока по 2 — в резьбовые заклёпки M4;",
        "• заклёпки ставятся снаружи; бортик (Ø≈9) входит",
        "  в отв. Ø10 борта крышки, винт с шайбой Ø12;",
        "• винты не попадают на уголки DIN и винты корыта;",
        "• рейка с проводами остаётся в модуле;",
        "• табло кассы 58×26 и кнопка Ø16 — по центру внизу",
        "  (за серединой — DIN-рейка), гравировка над ними.",
    ]), fontsize=8.8, color=INK, va="top", transform=ax.transAxes, linespacing=1.55)
    pdf.savefig(fig); plt.close(fig)

    page("Модуль табло: лицо и Z-скоба", 3, [([0.02, 0.45, 0.96, 0.48], "T1"), ([0.02, 0.05, 0.60, 0.36], "T2")])
    page("Модуль табло: П-обечайка", 4, [([0.02, 0.10, 0.96, 0.80], "T3")])
    page("Модуль табло: корыто и уголок", 5, [([0.02, 0.40, 0.96, 0.53], "T4"), ([0.02, 0.05, 0.50, 0.30], "T5")])
    page("Модуль табло: шаблон дверцы", 6, [([0.02, 0.06, 0.70, 0.86], "T7")])
print(pdf_path)
