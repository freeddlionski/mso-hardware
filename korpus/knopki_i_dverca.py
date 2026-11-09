"""Блок кнопок МСО и компоновка дверцы поста в двух вариантах (вертикальная и горизонтальная оплата), без размеров."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle, FancyBboxPatch

OUT = sys.argv[1]
plt.rcParams["font.family"] = "DejaVu Sans"
STEEL, STEEL_D, STEEL_DD, EDGE, INK = "#d9dde1", "#b7bdc4", "#9aa2ab", "#4a5560", "#2b3138"
GLASS, DARK, MATRIX, LED = "#9fd3e6", "#23272c", "#15191e", "#3fd7b6"
NAMES = ["ПЕНА", "ВОДА", "ШАМПУНЬ", "ВОСК", "ОСМОС", "ДИСКИ", "ВОЗДУХ", "ПАУЗА"]


def R(ax, x, y, w, h, fc, ec=EDGE, lw=1.1, z=2, alpha=1.0):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha))


def RR(ax, x, y, w, h, fc, rr=6, z=2, lw=1.1, ec=EDGE):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={rr}", fc=fc, ec=ec, lw=lw, zorder=z))


def button(ax, cx, cy, r=9, lit=False, z=5):
    ax.add_patch(Circle((cx, cy), r + 2.5, fc="#c8cdd2", ec=EDGE, lw=1, zorder=z))
    ax.add_patch(Circle((cx, cy), r + 0.8, fc="none", ec=("#59d0ff" if lit else "#9aa2ab"), lw=2, zorder=z + 0.1))
    ax.add_patch(Circle((cx, cy), r - 1.5, fc="#e9ecef", ec=EDGE, lw=0.8, zorder=z + 0.2))


def display(ax, x, y, w, h):
    R(ax, x, y, w, h, MATRIX, z=4)
    for r in range(6):
        for c in range(int(w / 9)):
            ax.add_patch(Circle((x + 6 + c * 9, y + 7 + r * (h - 12) / 5), 1.2, fc=LED, ec="none", zorder=5, alpha=0.8))


def door(ax, x, y, w, h):
    R(ax, x, y, w, h, STEEL_DD, z=1)
    R(ax, x, y, w, h, GLASS, z=1.2, alpha=0.32)


def niche_v(ax, x, y):
    RR(ax, x - 6, y - 6, 112, 232, "#7b848d", 8, 2, 1.3)
    RR(ax, x, y, 100, 220, STEEL, 6, 3)
    ax.add_patch(Polygon([(x - 10, y + 230), (x + 110, y + 230), (x + 116, y + 240), (x - 16, y + 240)], closed=True, fc=STEEL, ec=EDGE, zorder=4))
    RR(ax, x + 18, y + 150, 64, 56, DARK, 5, 4); R(ax, x + 25, y + 157, 50, 40, "#f2f4f6", z=5)
    RR(ax, x + 12, y + 88, 76, 46, DARK, 4, 4); R(ax, x + 20, y + 118, 60, 5, "#ff4d4d", ec="none", z=5)
    R(ax, x + 28, y + 26, 44, 46, DARK, z=4); R(ax, x + 46, y + 58, 7, 10, "#c9ced4", z=5); R(ax, x + 42, y + 34, 14, 16, "#f0ece2", z=5)
    ax.add_patch(Polygon([(x + 38, y + 4), (x + 62, y + 4), (x + 59, y + 16), (x + 41, y + 16)], closed=True, fc="#f3e2c7", ec=EDGE, zorder=5))


def niche_h(ax, x, y):
    RR(ax, x - 6, y - 6, 262, 102, "#7b848d", 8, 2, 1.3)
    RR(ax, x, y, 250, 90, STEEL, 6, 3)
    ax.add_patch(Polygon([(x - 10, y + 100), (x + 260, y + 100), (x + 266, y + 110), (x - 16, y + 110)], closed=True, fc=STEEL, ec=EDGE, zorder=4))
    RR(ax, x + 14, y + 14, 64, 62, DARK, 5, 4); R(ax, x + 21, y + 21, 50, 46, "#f2f4f6", z=5)
    RR(ax, x + 96, y + 22, 76, 46, DARK, 4, 4); R(ax, x + 104, y + 52, 60, 5, "#ff4d4d", ec="none", z=5)
    R(ax, x + 190, y + 24, 44, 46, DARK, z=4); R(ax, x + 208, y + 56, 7, 10, "#c9ced4", z=5); R(ax, x + 204, y + 32, 14, 16, "#f0ece2", z=5)
    ax.add_patch(Polygon([(x + 200, y + 4), (x + 224, y + 4), (x + 221, y + 16), (x + 203, y + 16)], closed=True, fc="#f3e2c7", ec=EDGE, zorder=5))


def btn_plate_v(ax, x, y, n=8):
    """Кнопки столбцом: надпись слева от кнопки."""
    h = n * 32 + 16
    RR(ax, x - 5, y - 5, 120, h + 10, "#7b848d", 6, 2, 1.2)
    R(ax, x, y, 110, h, STEEL, z=3)
    for i in range(n):
        cy = y + h - 24 - i * 32
        ax.text(x + 10, cy, NAMES[i], fontsize=7.6, color="#3a4048", va="center", fontweight="bold", zorder=6, family="DejaVu Sans")
        button(ax, x + 88, cy, 9, lit=(i == 1))
    for (px, py) in ((5, 5), (105, 5), (5, h - 5), (105, h - 5)):
        ax.add_patch(Circle((x + px, y + py), 1.8, fc="#5b646d", ec="none", zorder=4))


def btn_plate_h(ax, x, y, n=8):
    """Кнопки в ряд: надпись над кнопкой."""
    w = n * 36 + 14
    RR(ax, x - 5, y - 5, w + 10, 70, "#7b848d", 6, 2, 1.2)
    R(ax, x, y, w, 60, STEEL, z=3)
    for i in range(n):
        cx = x + 25 + i * 36
        ax.text(cx, y + 47, NAMES[i], fontsize=6, color="#3a4048", ha="center", va="center", fontweight="bold", zorder=6)
        button(ax, cx, y + 22, 9, lit=(i == 1))
    for (px, py) in ((5, 5), (w - 5, 5), (5, 55), (w - 5, 55)):
        ax.add_patch(Circle((x + px, y + py), 1.8, fc="#5b646d", ec="none", zorder=4))


fig = plt.figure(figsize=(19, 11))
fig.patch.set_facecolor("white")

# ================================================= Вариант 1: вертикальная оплата, кнопки столбцом рядом
ax = fig.add_axes([0.01, 0.07, 0.30, 0.86]); ax.set_aspect("equal"); ax.axis("off")
door(ax, 0, 0, 300, 520)
display(ax, 22, 400, 256, 100)
niche_v(ax, 30, 70)
btn_plate_v(ax, 165, 60)
ax.text(150, -22, "дисплей сверху · оплата слева · кнопки столбцом справа", fontsize=9, color=INK, ha="center")
ax.set_xlim(-20, 320); ax.set_ylim(-45, 545)
ax.set_title("Вариант 1: вертикальная оплата", fontsize=14, color=INK, fontweight="bold", pad=4)

# ================================================= Вариант 2: горизонтальная оплата, кнопки в ряд
ax = fig.add_axes([0.32, 0.07, 0.32, 0.86]); ax.set_aspect("equal"); ax.axis("off")
door(ax, 0, 0, 330, 470)
display(ax, 37, 350, 256, 100)
btn_plate_h(ax, 14, 250)
niche_h(ax, 40, 70)
ax.text(165, -22, "дисплей сверху · кнопки в ряд · оплата снизу", fontsize=9, color=INK, ha="center")
ax.set_xlim(-20, 350); ax.set_ylim(-45, 495)
ax.set_title("Вариант 2: горизонтальная оплата", fontsize=14, color=INK, fontweight="bold", pad=4)

# ================================================= Блок кнопок: устройство
ax = fig.add_axes([0.66, 0.40, 0.33, 0.53]); ax.set_aspect("equal"); ax.axis("off")
# разрез: стекло и дверца с проёмом, пластина кнопок изнутри на шпильках
R(ax, 0, 0, 6, 260, GLASS, z=3, alpha=0.85); R(ax, 6, 0, 4, 60, STEEL_DD, z=3); R(ax, 6, 200, 4, 60, STEEL_DD, z=3)
for sy in (45, 215):
    R(ax, 10, sy - 2, 36, 4, "#7d8790", z=4); R(ax, 30, sy - 6, 6, 12, "#5b646d", z=6)
R(ax, 10, 30, 4, 34, "#2f3338", z=4); R(ax, 10, 196, 4, 34, "#2f3338", z=4)
R(ax, 14, 30, 3, 200, STEEL, z=5)                                  # пластина кнопок с гравировкой
ax.text(5, 155, "ПЕНА", fontsize=7, color="#3a4048", rotation=90, ha="center", va="center", zorder=6)
for cy in (95, 165):                                               # кнопки сквозь пластину
    R(ax, -4, cy - 12, 21, 24, "#c8cdd2", z=6)                     # голова кнопки (выступает в проём стекла)
    R(ax, 17, cy - 8, 42, 16, "#9aa2ab", z=6)                      # корпус
    R(ax, 22, cy - 11, 6, 22, "#5b646d", z=7)                      # гайка
    ax.plot([59, 90, 120], [cy, cy, cy - 30], color=["#d33", "#3a7"][cy == 165], lw=1.8, zorder=5)
R(ax, 112, 60, 58, 100, "#23272c", z=5)
ax.text(141, 110, "Slave 1\n(в основном\nмодуле)", fontsize=7, color="white", ha="center", va="center", zorder=6)


def lab(xy, t, xt):
    ax.annotate(t, xy=xy, xytext=xt, fontsize=9.3, color=INK, va="center", zorder=50, linespacing=1.25,
                arrowprops=dict(arrowstyle="-", color="#6b7580", lw=0.9))


lab((3, 240), "стекло дверцы: вырез под кнопки", (45, 285))
lab((16, 130), "пластина кнопок: нержавейка,\nотверстия + гравировка надписей", (175, 245))
lab((35, 215), "закладные шпильки, уплотнитель, гайки", (175, 205))
lab((25, 95), "антивандальная кнопка с подсветкой,\nIP65, крепится своей гайкой", (175, 150))
lab((95, 140), "провода — напрямую на клеммы,\nбез разъёмов (собирается один раз)", (175, 90))
ax.set_xlim(-15, 420); ax.set_ylim(-10, 300)
ax.set_title("Блок кнопок: разрез", fontsize=14, color=INK, fontweight="bold", pad=4)

# ================================================= Заметки
ax = fig.add_axes([0.66, 0.05, 0.33, 0.32]); ax.axis("off")
notes = [
    "• Мест под кнопки — 8 (Slave 1 на 8 входов);\n   для 16 кнопок — модуль 16+16 и пластина под 16.",
    "• Смена функции — замена пластины с надписями: гайки кнопок\n   откручиваются, кнопки переставляются на новую пластину.",
    "• Вариант 1: кнопки столбцом, надпись слева — дверца уже,\n   удобно, когда оплата вертикальная.",
    "• Вариант 2: кнопки в ряд, надпись над кнопкой — дверца шире,\n   надписи короче (до 7–8 букв при 8 кнопках).",
    "• Кнопки на высоте руки (≈1,0–1,3 м от пола), дисплей — выше,\n   на уровне глаз.",
    "• Надписи — примеры; на табло у кнопки видны название и цена.",
]
for i, t in enumerate(notes):
    ax.text(0, 1 - i * 0.17, t, fontsize=9.3, color=INK, va="top", transform=ax.transAxes, linespacing=1.3)

fig.text(0.5, 0.01, "Блок кнопок и компоновка дверцы МСО74 — схематично, без размеров", ha="center", fontsize=9.5, color="#7a838c")
fig.savefig(OUT, dpi=140, facecolor="white")
print(OUT)
