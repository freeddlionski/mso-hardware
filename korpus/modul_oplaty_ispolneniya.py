"""Модуль оплаты МСО: два исполнения — вертикальное и горизонтальное (вид спереди и вставные пластины), без размеров."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle, FancyBboxPatch

OUT = sys.argv[1]
plt.rcParams["font.family"] = "DejaVu Sans"
STEEL, STEEL_D, STEEL_DD, EDGE, INK = "#d9dde1", "#b7bdc4", "#9aa2ab", "#4a5560", "#2b3138"
GLASS, DARK = "#9fd3e6", "#23272c"


def R(ax, x, y, w, h, fc, ec=EDGE, lw=1.1, z=2, alpha=1.0):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha))


def RR(ax, x, y, w, h, fc, rr=6, z=2, lw=1.1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={rr}", fc=fc, ec=EDGE, lw=lw, zorder=z))


# ---- приборы (вид спереди); (x, y) — левый нижний угол
def vendotek(ax, x, y):
    RR(ax, x, y, 76, 72, DARK, 6, 4)
    R(ax, x + 8, y + 8, 60, 50, "#f2f4f6", z=5)
    ax.text(x + 38, y + 42, "БАНКОВСКАЯ\nКАРТА", fontsize=5.5, color=INK, ha="center", va="center", zorder=6)
    ax.text(x + 38, y + 19, "QR", fontsize=8, color="#2a5bd7", ha="center", va="center", fontweight="bold", zorder=6)


def bill(ax, x, y, vertical_slot=False):
    RR(ax, x, y, 88, 58, DARK, 4, 4)
    R(ax, x + 10, y + 36, 68, 6, "#ff4d4d", ec="none", z=5)
    ax.text(x + 44, y + 16, "купюрник", fontsize=7, color="#cfd4d9", ha="center", zorder=5)


def coin(ax, x, y):
    R(ax, x, y, 56, 58, DARK, z=4)
    R(ax, x + 24, y + 42, 8, 12, "#c9ced4", z=5)
    R(ax, x + 20, y + 10, 16, 20, "#f0ece2", z=5)


def cup(ax, cx, y):
    ax.add_patch(Polygon([(cx - 16, y), (cx + 16, y), (cx + 12, y + 14), (cx - 12, y + 14)], closed=True, fc="#f3e2c7", ec=EDGE, lw=1, zorder=5))
    ax.text(cx, y + 6, "возврат", fontsize=5.3, color=INK, ha="center", va="center", zorder=6)


def niche(ax, x, y, w, h):
    """Дверца со стеклом, проём ниши с козырьком, дно ниши (видно как светлая пластина)."""
    R(ax, x - 30, y - 30, w + 60, h + 75, STEEL_DD, z=1)
    R(ax, x - 30, y - 30, w + 60, h + 75, GLASS, z=1.2, alpha=0.35)
    RR(ax, x - 8, y - 8, w + 16, h + 16, "#7b848d", 8, 2, 1.4)
    RR(ax, x, y, w, h, STEEL, 6, 3)
    ax.add_patch(Polygon([(x - 12, y + h + 12), (x + w + 12, y + h + 12), (x + w + 20, y + h + 24), (x - 20, y + h + 24)],
                         closed=True, fc=STEEL, ec=EDGE, lw=1.1, zorder=4))


def plate(ax, x, y, w, h, holes, blank=None, title=""):
    R(ax, x, y, w, h, STEEL, z=2)
    for (hx, hy, hw, hh) in holes:
        R(ax, x + hx, y + hy, hw, hh, "white", z=3)
    if blank:
        bx, by, bw, bh = blank
        R(ax, x + bx, y + by, bw, bh, STEEL_DD, z=3)
        for (px, py) in ((4, 4), (bw - 4, 4), (4, bh - 4), (bw - 4, bh - 4)):
            ax.add_patch(Circle((x + bx + px, y + by + py), 1.7, fc="#5b646d", ec="none", zorder=4))
        ax.text(x + bx + bw / 2, y + by + bh / 2, "заглушка", fontsize=6.5, color=INK, ha="center", va="center", zorder=4)
    for (px, py) in ((7, 7), (w - 7, 7), (7, h - 7), (w - 7, h - 7)):
        ax.add_patch(Circle((x + px, y + py), 2.4, fc="white", ec=EDGE, lw=0.8, zorder=3))
    ax.text(x + w / 2, y - 14, title, fontsize=8.5, color=INK, ha="center", va="center")


fig = plt.figure(figsize=(18, 11.5))
fig.patch.set_facecolor("white")

# ======================================================== Вертикальное исполнение
ax = fig.add_axes([0.02, 0.06, 0.40, 0.86]); ax.set_aspect("equal"); ax.axis("off")
NX, NY, NW, NH = 0, 0, 130, 280
niche(ax, NX, NY, NW, NH)
vendotek(ax, 27, 196)
bill(ax, 21, 116)
coin(ax, 37, 40)
cup(ax, 65, 10)
ax.text(65, -55, "Вид спереди", fontsize=10, color=INK, ha="center")
plate(ax, 220, 40, 100, 230, [(12, 160, 76, 62), (6, 95, 88, 48), (22, 20, 56, 54)], None, "с монетником")
plate(ax, 345, 40, 100, 230, [(12, 160, 76, 62), (6, 95, 88, 48)], (22, 20, 56, 54), "без монетника")
ax.text(332, 300, "Вставные пластины", fontsize=10, color=INK, ha="center")
ax.set_xlim(-45, 460); ax.set_ylim(-75, 345)
ax.set_title("Вертикальное исполнение", fontsize=15, color=INK, fontweight="bold", pad=4)

# ======================================================== Горизонтальное исполнение
ax = fig.add_axes([0.44, 0.47, 0.55, 0.45]); ax.set_aspect("equal"); ax.axis("off")
NX, NY, NW, NH = 0, 0, 300, 112
niche(ax, NX, NY, NW, NH)
vendotek(ax, 18, 28)          # слева
bill(ax, 112, 34)             # в середине
coin(ax, 224, 34)             # монетник — с краю: без него заглушка не «дыра» посередине
cup(ax, 252, 6)
ax.text(150, -52, "Вид спереди: Vendotek — купюрник — монетник (монетник с краю)", fontsize=9, color=INK, ha="center")
ax.set_xlim(-45, 345); ax.set_ylim(-65, 160)
ax.set_title("Горизонтальное исполнение", fontsize=15, color=INK, fontweight="bold", pad=4)

ax = fig.add_axes([0.44, 0.17, 0.55, 0.27]); ax.set_aspect("equal"); ax.axis("off")
plate(ax, 0, 0, 290, 92, [(14, 14, 76, 64), (106, 22, 88, 48), (216, 18, 56, 56)], None, "с монетником")
plate(ax, 310, 0, 290, 92, [(14, 14, 76, 64), (106, 22, 88, 48)], (216, 18, 56, 56), "без монетника: заглушка с краю")
ax.text(300, 112, "Вставные пластины", fontsize=10, color=INK, ha="center")
ax.set_xlim(-10, 610); ax.set_ylim(-30, 125)

# ======================================================== Сравнение
ax = fig.add_axes([0.44, 0.02, 0.55, 0.14]); ax.axis("off")
rows = [
    ("", "Вертикальное", "Горизонтальное"),
    ("Место на дверце", "узкая и высокая ниша", "широкая и низкая ниша"),
    ("Удобство клиенту", "приборы на разной высоте", "всё на одной высоте, удобнее всего"),
    ("Внутри шкафа", "ящик для монет и кассета — друг под другом", "рядом; одна длинная полка под всем"),
    ("Козырёк, вода", "короткий козырёк, дно ниши маленькое", "длинный козырёк, дно ниши длинное — уклон обязателен"),
]
for i, (a, b, c) in enumerate(rows):
    y = 1 - i * 0.2
    w = "bold" if i == 0 else "normal"
    ax.text(0.0, y, a, fontsize=9.3, color=INK, fontweight="bold", va="top", transform=ax.transAxes)
    ax.text(0.22, y, b, fontsize=9.3, color=INK, fontweight=w, va="top", transform=ax.transAxes)
    ax.text(0.58, y, c, fontsize=9.3, color=INK, fontweight=w, va="top", transform=ax.transAxes)

fig.text(0.5, 0.005, "Модуль оплаты МСО74 — два исполнения, схематично, без размеров. Разрез и сборка одинаковы для обоих (korpus/modul_oplaty_eskiz.png)",
         ha="center", fontsize=9, color="#7a838c")
fig.savefig(OUT, dpi=140, facecolor="white")
print(OUT)
