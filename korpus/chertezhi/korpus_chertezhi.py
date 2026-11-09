"""Чертежи шкафа поста МСО74, черновик v0.1 (Павел 2026-11-07): компоновка «вариант 2» — табло сверху, 8 кнопок в ряд,
горизонтальная оплата Vendotek — купюрник — монетник. Выход: PDF (A3, листы с размерами) и DXF R12 под лазер (контуры реза,
слой ENGRAVE — гравировка, слой MARK — разметка: приварные шпильки, линии сварки).
Запуск: python3 korpus_chertezhi.py <папка вывода>. Размеры в мм."""
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Polygon, Rectangle

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
plt.rcParams["font.family"] = "DejaVu Sans"
INK, CUT, MARKC, ENGR, DIM = "#1f2328", "#1f2328", "#c0392b", "#2b6cb0", "#5b6670"
VERSION = "v0.1 черновик — сверить с деталями по месту перед заказом"


# ============================================================ детали (локальные координаты: левый нижний угол = 0,0)
class Part:
    def __init__(self, key, title, w, h, thick, r=0.0, qty=1, note=""):
        self.key, self.title, self.w, self.h, self.t, self.r, self.qty, self.note = key, title, w, h, thick, r, qty, note
        self.cuts = []      # ("rect", cx, cy, w, h, r) | ("circle", cx, cy, d)
        self.marks = []     # ("stud", x, y, label) | ("line", x1, y1, x2, y2)
        self.texts = []     # (x, y, h, text) — гравировка, по центру

    def rect(self, cx, cy, w, h, r=0.0):
        self.cuts.append(("rect", cx, cy, w, h, r)); return self

    def hole(self, cx, cy, d):
        self.cuts.append(("circle", cx, cy, d)); return self

    def stud(self, x, y, label="M5"):
        self.marks.append(("stud", x, y, label)); return self

    def text(self, x, y, h, s):
        self.texts.append((x, y, h, s)); return self


def rrect_segments(x0, y0, w, h, r):
    """Контур скруглённого прямоугольника: отрезки и дуги (центр, радиус, угол от, до)."""
    lines, arcs = [], []
    if r <= 0:
        pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
        return [(pts[i], pts[(i + 1) % 4]) for i in range(4)], []
    lines = [((x0 + r, y0), (x0 + w - r, y0)), ((x0 + w, y0 + r), (x0 + w, y0 + h - r)),
             ((x0 + w - r, y0 + h), (x0 + r, y0 + h)), ((x0, y0 + h - r), (x0, y0 + r))]
    arcs = [((x0 + w - r, y0 + r), r, 270, 360), ((x0 + w - r, y0 + h - r), r, 0, 90),
            ((x0 + r, y0 + h - r), r, 90, 180), ((x0 + r, y0 + r), r, 180, 270)]
    return lines, arcs


# ------------------------------------------------------------ DXF R12 (свой минимальный писатель: ezdxf не установлен)
def write_dxf(part, path):
    ents = []

    def line(a, b, layer):
        ents.append(f"0\nLINE\n8\n{layer}\n10\n{a[0]:.3f}\n20\n{a[1]:.3f}\n30\n0\n11\n{b[0]:.3f}\n21\n{b[1]:.3f}\n31\n0")

    def arc(c, r, a0, a1, layer):
        ents.append(f"0\nARC\n8\n{layer}\n10\n{c[0]:.3f}\n20\n{c[1]:.3f}\n30\n0\n40\n{r:.3f}\n50\n{a0:.3f}\n51\n{a1:.3f}")

    def circle(c, r, layer):
        ents.append(f"0\nCIRCLE\n8\n{layer}\n10\n{c[0]:.3f}\n20\n{c[1]:.3f}\n30\n0\n40\n{r:.3f}")

    def text(x, y, h, s, layer):
        ents.append(f"0\nTEXT\n8\n{layer}\n10\n{x:.3f}\n20\n{y:.3f}\n30\n0\n40\n{h:.3f}\n1\n{s}\n72\n1\n73\n2\n11\n{x:.3f}\n21\n{y:.3f}\n31\n0")

    ls, ars = rrect_segments(0, 0, part.w, part.h, part.r)
    for a, b in ls: line(a, b, "CUT")
    for c, r, a0, a1 in ars: arc(c, r, a0, a1, "CUT")
    for f in part.cuts:
        if f[0] == "circle":
            circle((f[1], f[2]), f[3] / 2, "CUT")
        else:
            _, cx, cy, w, h, r = f
            ls, ars = rrect_segments(cx - w / 2, cy - h / 2, w, h, r)
            for a, b in ls: line(a, b, "CUT")
            for c, rr, a0, a1 in ars: arc(c, rr, a0, a1, "CUT")
    for m in part.marks:
        if m[0] == "stud":
            x, y = m[1], m[2]
            line((x - 4, y), (x + 4, y), "MARK"); line((x, y - 4), (x, y + 4), "MARK"); circle((x, y), 2.5, "MARK")
        else:
            line((m[1], m[2]), (m[3], m[4]), "MARK")
    for x, y, h, s in part.texts:
        text(x, y, h, s, "ENGRAVE")
    head = ("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n9\n$DWGCODEPAGE\n3\nANSI_1251\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n"
            "0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n3\n"
            "0\nLAYER\n2\nCUT\n70\n0\n62\n7\n6\nCONTINUOUS\n"
            "0\nLAYER\n2\nENGRAVE\n70\n0\n62\n5\n6\nCONTINUOUS\n"
            "0\nLAYER\n2\nMARK\n70\n0\n62\n1\n6\nCONTINUOUS\n0\nENDTAB\n0\nENDSEC\n")
    body = "0\nSECTION\n2\nENTITIES\n" + "\n".join(ents) + "\n0\nENDSEC\n0\nEOF\n"
    with open(path, "w", encoding="cp1251", newline="\r\n") as f:
        f.write(head + body)


# ============================================================ геометрия шкафа (вариант 2)
DOOR_W, DOOR_H, CAB_D = 520, 1000, 260
DISP_C = (260, 860)            # центр окна табло на дверце
BTN_C = (260, 650)             # центр выреза под кнопки
PAY_C = (260, 440)             # центр ниши оплаты

door = Part("01_dverca", "Дверца (лист 1,5–2 мм)", DOOR_W, DOOR_H, 2, r=0, note="петли и замок — по выбранной фурнитуре")
door.rect(*DISP_C, 262, 133, 3)                      # окно табло
door.rect(*BTN_C, 360, 80, 3)                        # вырез кнопок
door.rect(*PAY_C, 420, 200, 8)                       # проём ниши оплаты
for x in (105, 260, 415):                            # шпильки основного модуля (рамка 310×220)
    for y in (750, 970):
        door.stud(x, y)
door.stud(105, 860); door.stud(415, 860)
for x in (70, 260, 450):                             # шпильки пластины кнопок (рамка 380×100)
    for y in (600, 700):
        door.stud(x, y)
for x in (37.5, 260, 482.5):                         # шпильки корыта оплаты (рамка 445×225)
    for y in (327.5, 552.5):
        door.stud(x, y)
door.stud(37.5, 440); door.stud(482.5, 440)

# --- основной модуль
face = Part("02_modul_lico", "Основной модуль: лицевая пластина (2 мм)", 340, 250, 2, r=4)
face.rect(170, 125, 258, 129, 1)                     # окно: матрица 256×127 заподлицо, по 1 мм зазора
for (x, y) in ((15, 15), (170, 15), (325, 15), (15, 235), (170, 235), (325, 235), (15, 125), (325, 125)):
    face.hole(x, y, 5.5)                             # под шпильки дверцы M5
face.marks.append(("line", 37.5, 30.5, 302.5, 30.5)); face.marks.append(("line", 302.5, 30.5, 302.5, 219.5))
face.marks.append(("line", 302.5, 219.5, 37.5, 219.5)); face.marks.append(("line", 37.5, 219.5, 37.5, 30.5))

bar = Part("03_modul_planka", "Планка-«лапка» под матрицу (2 мм), 2 шт.", 262, 20, 2, qty=2,
           note="приварить к боковым стенкам обечайки так, чтобы лицо планки было в 19 мм от лица модуля")
for x in (15, 92, 169, 245.5):
    bar.hole(x, 10, 3.4)                             # винты M3 в стойки матрицы

back = Part("04_modul_kryshka", "Основной модуль: задняя крышка (2 мм)", 265, 189, 2, r=3)
for (x, y) in ((8, 8), (132.5, 8), (257, 8), (8, 181), (132.5, 181), (257, 181), (8, 94.5), (257, 94.5)):
    back.hole(x, y, 4.5)                             # невыпадающие винты M4 в заклёпки-гайки отгиба
back.rect(75, 48, 58, 26, 1)                         # табло кассы DM56A04 (посадка 58×26)
back.hole(190, 58, 16)                               # кнопка настройки Ø16
back.text(75, 74, 6, "КАССА"); back.text(190, 82, 5, "НАСТРОЙКИ"); back.text(190, 33, 3.5, "удержание — инкассация")

bottom = Part("05_modul_dno", "Основной модуль: дно обечайки (развёртка стенки 265×130, 1,5 мм)", 265, 130, 1.5,
              note="сальники снизу: 3× M20 (Ø20,5), мембранный клапан M12 (Ø12,5)")
for x in (60, 110, 160):
    bottom.hole(x, 65, 20.5)
bottom.hole(215, 65, 12.5)

# --- кнопки
NAMES = [("ТУРБО", "СУШКА"), ("ПЕНА", "ЩЁТКА"), ("АКТИВНАЯ", "ХИМИЯ"), ("ВОДА", ""), ("ВОСК", ""), ("ОСМОС", ""),
         ("ШАМПУНЬ", ""), ("ПАУЗА", "")]
btn = Part("06_knopki", "Пластина кнопок (2 мм, гравировка)", 400, 120, 2, r=3,
           note="надписи 4–8 — примеры, уточнить; смена функции = новая пластина")
for i, (l1, l2) in enumerate(NAMES):
    x = 53 + i * 42
    btn.hole(x, 50, 19)
    if l2:
        btn.text(x, 86, 5, l1); btn.text(x, 76, 5, l2)
    else:
        btn.text(x, 81, 5, l1)
for (x, y) in ((10, 10), (200, 10), (390, 10), (10, 110), (200, 110), (390, 110)):
    btn.hole(x, y, 5.5)

# --- оплата
flange = Part("07_koryto_flanec", "Корыто оплаты: фланец (2 мм)", 470, 250, 2, r=6)
flange.rect(235, 125, 420, 200, 8)
for (x, y) in ((12.5, 12.5), (235, 12.5), (457.5, 12.5), (12.5, 237.5), (235, 237.5), (457.5, 237.5), (12.5, 125), (457.5, 125)):
    flange.hole(x, y, 5.5)

lip = Part("08_koryto_ramka", "Корыто оплаты: задняя рамка-отгиб (2 мм)", 423, 203, 2, r=4,
           note="приварить к задней кромке стенок корыта (глубина 60); в отверстия — заклёпки-гайки M4")
lip.rect(211.5, 101.5, 380, 160, 6)
for (x, y) in ((11, 11), (211.5, 11), (412, 11), (11, 192), (211.5, 192), (412, 192), (11, 101.5), (412, 101.5)):
    lip.hole(x, y, 6.1)                              # под заклёпку-гайку M4

plate = Part("09_oplata_plastina", "Вставная пластина оплаты (2 мм), с монетником", 440, 220, 2, r=4,
             note="шпильки купюрника — приварить по месту; отверстия рамки монетника — разметить по рамке")
VX, BX, CX, PY = 95, 228, 352, 110
plate.hole(VX, PY, 60)                               # Vendotek: проводка Ø60
for dx in (-32.5, 32.5):
    for dy in (-43.5, 43.5):
        plate.hole(VX + dx, PY + dy, 4.5)            # шпильки Vendotek 65×87
plate.rect(BX, PY, 86, 111, 2)                       # купюрник (с запасом)
plate.rect(CX, PY, 50, 105, 2)                       # монетник: рамка 60×120 накладная, с лотком возврата
for (x, y) in ((19.5, 19.5), (220, 19.5), (420.5, 19.5), (19.5, 200.5), (220, 200.5), (420.5, 200.5), (19.5, 110), (420.5, 110)):
    plate.hole(x, y, 4.5)

plate_nc = Part("10_oplata_plastina_bez_monetnika", "Вставная пластина оплаты без монетника (2 мм)", 440, 220, 2, r=4,
                note="на месте монетника — без выреза")
plate_nc.cuts = [c for c in plate.cuts if not (c[0] == "rect" and abs(c[1] - CX) < 1)]

PARTS = [door, face, bar, back, bottom, btn, flange, lip, plate, plate_nc]


# ============================================================ рисование
def draw_part(ax, p, ox=0, oy=0, show_studs=True):
    ax.add_patch(FancyBboxPatch((ox, oy), p.w, p.h, boxstyle=f"round,pad=0,rounding_size={p.r}" if p.r else "square,pad=0",
                                fc="#eef1f4", ec=CUT, lw=1.1, zorder=2))
    for f in p.cuts:
        if f[0] == "circle":
            ax.add_patch(Circle((ox + f[1], oy + f[2]), f[3] / 2, fc="white", ec=CUT, lw=0.9, zorder=3))
        else:
            _, cx, cy, w, h, r = f
            ax.add_patch(FancyBboxPatch((ox + cx - w / 2, oy + cy - h / 2), w, h,
                                        boxstyle=f"round,pad=0,rounding_size={r}" if r else "square,pad=0",
                                        fc="white", ec=CUT, lw=0.9, zorder=3))
    for m in p.marks:
        if m[0] == "stud" and show_studs:
            x, y = ox + m[1], oy + m[2]
            ax.plot([x - 5, x + 5], [y, y], color=MARKC, lw=0.8, zorder=4); ax.plot([x, x], [y - 5, y + 5], color=MARKC, lw=0.8, zorder=4)
            ax.add_patch(Circle((x, y), 2.5, fc="none", ec=MARKC, lw=0.8, zorder=4))
        elif m[0] == "line":
            ax.plot([ox + m[1], ox + m[3]], [oy + m[2], oy + m[4]], color=MARKC, lw=0.8, ls="--", zorder=4)
    for x, y, h, s in p.texts:
        ax.text(ox + x, oy + y, s, fontsize=max(4.5, h * 1.05), color=ENGR, ha="center", va="center", zorder=5, fontweight="bold")


def dim(ax, p1, p2, off, txt=None, fs=7.5):
    """Размерная линия между p1 и p2 (горизонтальная или вертикальная), смещённая на off."""
    (x1, y1), (x2, y2) = p1, p2
    if abs(y1 - y2) < 1e-6 or abs(x1 - x2) > abs(y1 - y2):   # горизонтальный
        y = y1 + off
        ax.plot([x1, x1], [y1, y], color=DIM, lw=0.5); ax.plot([x2, x2], [y2, y], color=DIM, lw=0.5)
        ax.annotate("", xy=(x1, y), xytext=(x2, y), arrowprops=dict(arrowstyle="<->", color=DIM, lw=0.6, shrinkA=0, shrinkB=0))
        ax.text((x1 + x2) / 2, y + (2.5 if off >= 0 else -2.5), txt or f"{abs(x2 - x1):g}", fontsize=fs, color=DIM,
                ha="center", va="bottom" if off >= 0 else "top")
    else:
        x = x1 + off
        ax.plot([x1, x], [y1, y1], color=DIM, lw=0.5); ax.plot([x2, x], [y2, y2], color=DIM, lw=0.5)
        ax.annotate("", xy=(x, y1), xytext=(x, y2), arrowprops=dict(arrowstyle="<->", color=DIM, lw=0.6, shrinkA=0, shrinkB=0))
        ax.text(x + (2.5 if off >= 0 else -2.5), (y1 + y2) / 2, txt or f"{abs(y2 - y1):g}", fontsize=fs, color=DIM,
                ha="left" if off >= 0 else "right", va="center", rotation=90)


def features_table(p):
    rows = []
    for f in p.cuts:
        if f[0] == "circle":
            rows.append(f"Ø{f[3]:g} — центр ({f[1]:g}; {f[2]:g})")
        else:
            rows.append(f"вырез {f[3]:g}×{f[4]:g}{' R' + format(f[5], 'g') if f[5] else ''} — центр ({f[1]:g}; {f[2]:g})")
    studs = [m for m in p.marks if m[0] == "stud"]
    if studs:
        xs = sorted({m[1] for m in studs}); ys = sorted({m[2] for m in studs})
        rows.append(f"приварные шпильки M5 ×{len(studs)}: x {', '.join(f'{v:g}' for v in xs)}; y {', '.join(f'{v:g}' for v in ys)}")
    return rows


def sheet(pdf, title, num):
    fig = plt.figure(figsize=(16.54, 11.69))
    fig.patch.set_facecolor("white")
    fig.text(0.015, 0.975, f"МСО74 · Шкаф поста · {title}", fontsize=15, fontweight="bold", color=INK, va="top")
    fig.text(0.985, 0.975, f"Лист {num}", fontsize=11, color=INK, ha="right", va="top")
    fig.text(0.015, 0.012, f"{VERSION}. Размеры в мм; координаты — от левого нижнего угла детали. "
             "Красное — разметка (шпильки, сварка), синее — гравировка. DXF — в той же папке.", fontsize=8.5, color="#6b7580")
    return fig


def part_block(fig, rect, p, show_table=True, scale_note=True):
    ax = fig.add_axes(rect); ax.set_aspect("equal"); ax.axis("off")
    draw_part(ax, p)
    dim(ax, (0, 0), (p.w, 0), -p.h * 0.08 - 8)
    dim(ax, (0, 0), (0, p.h), -p.w * 0.06 - 8)
    ax.set_title(f"{p.key[:2]}. {p.title}" + (f" — {p.qty} шт." if p.qty > 1 and "шт" not in p.title else ""), fontsize=10.5,
                 color=INK, fontweight="bold", loc="left", pad=4)
    pad = max(p.w, p.h) * 0.12 + 14
    ax.set_xlim(-pad, p.w + 10); ax.set_ylim(-pad, p.h + 8)
    if show_table:
        import textwrap
        rows = features_table(p) + (textwrap.wrap(f"Примечание: {p.note}", 58) if p.note else [])
        ax.text(p.w + 14, p.h, "\n".join(rows[:22]), fontsize=7.2, color=INK, va="top", linespacing=1.35)
        ax.set_xlim(-pad, p.w + 10 + p.w * 0.95)
    return ax


with PdfPages(os.path.join(OUT, "shkaf_chertezhi.pdf")) as pdf:
    # -------------------------------------------------- лист 1: общий вид
    fig = sheet(pdf, "Общий вид (вариант 2: кнопки в ряд, оплата горизонтально)", 1)
    ax = fig.add_axes([0.03, 0.05, 0.40, 0.88]); ax.set_aspect("equal"); ax.axis("off")
    draw_part(ax, door)
    ax.add_patch(Rectangle(((DOOR_W - 256) / 2, 860 - 63.5), 256, 127, fc="#15191e", ec="none", zorder=3.5, alpha=0.85))
    for i in range(8):
        ax.add_patch(Circle((113 + i * 42, 640), 9.5, fc="#d6dade", ec=CUT, lw=0.8, zorder=4))
        l1, l2 = NAMES[i]
        ax.text(113 + i * 42, 672, l1 + ("\n" + l2 if l2 else ""), fontsize=4.6, color=ENGR, ha="center", va="center", zorder=5)
    for (cx, w, h, lab) in ((PAY_C[0] - 125, 100, 130, "Vendotek"), (PAY_C[0] + 8, 86, 111, "купюрник"), (PAY_C[0] + 132, 60, 120, "монетник")):
        ax.add_patch(Rectangle((cx - w / 2, PAY_C[1] - h / 2), w, h, fc="#2a2f35", ec=CUT, lw=0.8, zorder=4))
        ax.text(cx, PAY_C[1], lab, fontsize=6.5, color="white", ha="center", va="center", rotation=90, zorder=5)
    dim(ax, (0, 0), (DOOR_W, 0), -40); dim(ax, (0, 0), (0, DOOR_H), -45)
    dim(ax, (DOOR_W, 0), (DOOR_W, DISP_C[1]), 30, f"{DISP_C[1]} (центр табло)")
    dim(ax, (DOOR_W, 0), (DOOR_W, BTN_C[1]), 60, f"{BTN_C[1]} (центр кнопок)")
    dim(ax, (DOOR_W, 0), (DOOR_W, PAY_C[1]), 90, f"{PAY_C[1]} (центр оплаты)")
    ax.set_xlim(-80, DOOR_W + 130); ax.set_ylim(-75, DOOR_H + 25)
    ax.set_title("Дверца снаружи (приборы показаны условно)", fontsize=11, color=INK, fontweight="bold", loc="left")

    # разрез сбоку
    ax = fig.add_axes([0.45, 0.05, 0.24, 0.88]); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((0, 0), 6, DOOR_H, fc="#9fd3e6", ec=CUT, lw=0.8, zorder=3))          # стекло
    ax.add_patch(Rectangle((6, 0), 2, DOOR_H, fc="#9aa2ab", ec=CUT, lw=0.8, zorder=3))          # дверца
    ax.add_patch(Rectangle((8, 0), CAB_D - 8, DOOR_H, fc="none", ec=CUT, lw=1.2, ls="-", zorder=2))   # корпус шкафа
    ax.add_patch(Rectangle((10, DISP_C[1] - 125), 2, 250, fc="#c8cdd2", ec=CUT, lw=0.8, zorder=4))  # лицо модуля
    ax.add_patch(Rectangle((12, DISP_C[1] - 94.5), 130, 189, fc="#e6e9ec", ec=CUT, lw=0.9, zorder=3.5))  # обечайка
    ax.add_patch(Rectangle((10, DISP_C[1] - 63.5), 19, 127, fc="#15191e", ec="none", zorder=4))  # матрица
    ax.add_patch(Rectangle((40, DISP_C[1] - 85), 70, 170, fc="#3a3f45", ec="none", zorder=4, alpha=0.7))
    ax.text(75, DISP_C[1], "DIN:\nESP32, Slave 1,\nБП 24→5", fontsize=6, color="white", ha="center", va="center", zorder=5)
    ax.add_patch(Rectangle((10, BTN_C[1] - 60), 2, 120, fc="#c8cdd2", ec=CUT, lw=0.8, zorder=4))
    ax.add_patch(Rectangle((12, BTN_C[1] - 20), 60, 14, fc="#9aa2ab", ec=CUT, lw=0.6, zorder=4))  # кнопка
    ax.add_patch(Rectangle((10, PAY_C[1] - 125), 2, 250, fc="#c8cdd2", ec=CUT, lw=0.8, zorder=4))   # фланец корыта
    ax.add_patch(Polygon([(12, PAY_C[1] + 100), (72, PAY_C[1] + 100), (72, PAY_C[1] - 96), (12, PAY_C[1] - 100)],
                         closed=True, fc="none", ec=CUT, lw=1, zorder=4))                          # корыто, дно с уклоном
    ax.add_patch(Rectangle((72, PAY_C[1] + 55 - 270), 120, 270, fc="#30363d", ec="none", zorder=4, alpha=0.75))
    ax.text(132, PAY_C[1] - 40, "купюрник\nс кассетой\n120 × 270\n(вниз от выреза —\nуточнить)", fontsize=6, color="white", ha="center", va="center", zorder=5)
    ax.add_patch(Rectangle((40, PAY_C[1] - 100 - 170), 110, 150, fc="none", ec="#8a6d3b", lw=1, ls="--", zorder=3.8))
    ax.text(95, PAY_C[1] - 255, "ящик монет\n(падают в 40–50\nот дверцы)", fontsize=6, color="#8a6d3b", ha="center", va="bottom")
    dim(ax, (0, 0), (CAB_D, 0), -40, f"{CAB_D} (глубина шкафа)")
    dim(ax, (12, DISP_C[1] + 94.5), (142, DISP_C[1] + 94.5), 25, "130")
    dim(ax, (12, PAY_C[1] + 100), (72, PAY_C[1] + 100), 18, "60")
    ax.text(5, DOOR_H + 15, "клиент", fontsize=8, color="#6b7580"); ax.text(CAB_D, DOOR_H + 15, "шкаф", fontsize=8, color="#6b7580", ha="right")
    ax.set_xlim(-30, CAB_D + 30); ax.set_ylim(-75, DOOR_H + 40)
    ax.set_title("Разрез сбоку", fontsize=11, color=INK, fontweight="bold", loc="left")

    ax = fig.add_axes([0.71, 0.05, 0.28, 0.88]); ax.axis("off")
    notes = [
        "ГАБАРИТ ШКАФА: 520 × 1000 × 260 мм (Ш × В × Г).",
        "Корпус — нержавейка AISI 304, 1,5 мм; дверца 1,5–2 мм.",
        "Стекло (или поликарбонат 4–6 мм, тонированный) во всю",
        "дверцу, вклеено снаружи; вырезы в стекле — под кнопки",
        "360×80 и под нишу оплаты 420×200 (закалённое — до закалки).",
        "",
        "ЗАКЛАДНЫЕ ШПИЛЬКИ M5 изнутри дверцы — приварить ДО",
        "вклейки стекла: модуль табло 8 шт., кнопки 6 шт.,",
        "корыто оплаты 8 шт. Все модули — через уплотнитель, гайки.",
        "",
        "ВЫСОТА УСТАНОВКИ: низ шкафа ≈ 500 мм от пола →",
        "кнопки ≈ 1150, центр табло ≈ 1360, оплата ≈ 940 мм.",
        "",
        "ОСНОВНОЙ МОДУЛЬ: лицо 340×250, обечайка 265×189×130",
        "(внутри 262×186: Slave 1 высотой 170 помещается),",
        "матрица 256×127×19 заподлицо, на 2 планках M3;",
        "DIN 250 мм; задняя крышка на 8 винтах M4.",
        "",
        "ОПЛАТА: корыто 420×200, глубина 60, дно с уклоном",
        "наружу 3–5°; рамка-отгиб с заклёпками-гайками M4;",
        "вставная пластина 440×220 (с монетником / без).",
        "Монетник: лоток возврата — в его рамке.",
        "Купюрник: 120 мм в глубину, 270 по высоте; кассета",
        "вынимается внутрь шкафа — место под ней не занимать.",
        "",
        "ОТКРЫТО (уточнить): козырёк над нишей (продолжение",
        "верхней стенки корыта наружу ~30 мм), петли и замок,",
        "крепление шкафа к стене, ввод кабелей в шкаф снизу,",
        "вывод антенны Wi-Fi, надписи кнопок 4–8.",
    ]
    ax.text(0, 1, "\n".join(notes), fontsize=9, color=INK, va="top", transform=ax.transAxes, linespacing=1.45)
    pdf.savefig(fig); plt.close(fig)

    # -------------------------------------------------- лист 2: дверца (раскрой)
    fig = sheet(pdf, "Дверца: вырезы и шпильки", 2)
    part_block(fig, [0.03, 0.05, 0.94, 0.88], door)
    pdf.savefig(fig); plt.close(fig)

    # -------------------------------------------------- лист 3: основной модуль
    fig = sheet(pdf, "Основной модуль (табло и контроллер)", 3)
    part_block(fig, [0.02, 0.50, 0.48, 0.44], face)
    part_block(fig, [0.52, 0.50, 0.47, 0.44], back)
    part_block(fig, [0.02, 0.27, 0.48, 0.20], bar)
    part_block(fig, [0.52, 0.06, 0.47, 0.38], bottom)
    ax = fig.add_axes([0.03, 0.05, 0.45, 0.20]); ax.axis("off")
    ax.text(0, 1, "Обечайка: 4 стенки 1,5 мм, наружу 265×189, глубина 130 от лица; сварка к лицевой пластине по красной линии.\n"
            "Задний отгиб внутрь 15 мм, 8 заклёпок-гаек M4 под крышку (по отверстиям крышки).\n"
            "Планки (лапки) — на глубине 19 мм от лица модуля, по рядам отверстий матрицы (12 и 115 от её низа).\n"
            "DIN-рейка 250 мм — на двух уголках к боковым стенкам, лицо рейки на глубине ≈ 30 мм;\n"
            "высота модулей на рейке до 70 мм → до крышки остаётся ≈ 25 мм на провода.",
            fontsize=8.5, color=INK, va="top", transform=ax.transAxes, linespacing=1.45)
    pdf.savefig(fig); plt.close(fig)

    # -------------------------------------------------- лист 4: кнопки и оплата
    fig = sheet(pdf, "Кнопки и модуль оплаты", 4)
    part_block(fig, [0.02, 0.66, 0.60, 0.29], btn)
    part_block(fig, [0.02, 0.35, 0.48, 0.30], flange)
    part_block(fig, [0.52, 0.35, 0.47, 0.30], lip)
    part_block(fig, [0.02, 0.04, 0.48, 0.30], plate)
    part_block(fig, [0.52, 0.04, 0.47, 0.30], plate_nc)
    ax = fig.add_axes([0.64, 0.68, 0.35, 0.26]); ax.axis("off")
    ax.text(0, 1, "Корыто: стенки 1,5 мм вокруг проёма 420×200, глубина 60;\n"
            "дно с уклоном к клиенту 3–5°; углы — сварка, сплошные.\n"
            "Рамка-отгиб — к задней кромке стенок, в неё заклёпки-гайки M4,\n"
            "вставная пластина — изнутри через уплотнитель.\n\n"
            "Кнопки Ø19, шаг 42 мм, антивандальные с подсветкой;\n"
            "видимая часть — вырез дверцы 360×80; гравировка 5 мм.",
            fontsize=8.5, color=INK, va="top", transform=ax.transAxes, linespacing=1.45)
    pdf.savefig(fig); plt.close(fig)

for p in PARTS:
    write_dxf(p, os.path.join(OUT, f"{p.key}.dxf"))
print("готово:", OUT, len(PARTS), "DXF")
