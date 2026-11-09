"""Эскиз модуля оплаты МСО (без размеров): ниша-корыто внутрь ящика, вставная пластина под приборы, монетник — опция."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle, FancyBboxPatch

OUT = sys.argv[1]
plt.rcParams["font.family"] = "DejaVu Sans"
STEEL, STEEL_D, STEEL_DD, EDGE, INK = "#d9dde1", "#b7bdc4", "#9aa2ab", "#4a5560", "#2b3138"
GLASS, RUBBER, DARK = "#9fd3e6", "#2f3338", "#23272c"


def R(ax, x, y, w, h, fc, ec=EDGE, lw=1.1, z=2, alpha=1.0):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha))


def PG(ax, pts, fc, ec=EDGE, lw=1.1, z=2, alpha=1.0):
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha))


def label(ax, xy, text, xytext, ha="left"):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=9.8, color=INK, ha=ha, va="center", zorder=50, linespacing=1.25,
                arrowprops=dict(arrowstyle="-", color="#6b7580", lw=0.9, shrinkA=2, shrinkB=1))


fig = plt.figure(figsize=(19, 10))
A = fig.add_axes([0.0, 0.04, 0.52, 0.90])
B = fig.add_axes([0.50, 0.30, 0.27, 0.64])
C = fig.add_axes([0.77, 0.30, 0.23, 0.64])
D = fig.add_axes([0.52, 0.03, 0.46, 0.25])
for ax in (A, B, C, D):
    ax.set_aspect("equal"); ax.axis("off")
fig.patch.set_facecolor("white")

# ===================================================================== A. Разрез сбоку
ax = A
OY0, OY1 = 40, 300            # проём в дверце под нишу
# стекло снаружи — с вырезом под нишу
R(ax, 0, -40, 6, OY0 + 40, GLASS, z=3, alpha=0.85)
R(ax, 0, OY1, 6, 60, GLASS, z=3, alpha=0.85)
# стальная дверца с проёмом
R(ax, 6, -40, 4, OY0 + 40, STEEL_DD, z=3)
R(ax, 6, OY1, 4, 60, STEEL_DD, z=3)
ax.text(-40, 368, "клиент", fontsize=10, color="#6b7580")
ax.text(300, 368, "шкаф", fontsize=10, color="#6b7580", ha="right")
# козырёк над нишей (отгиб наружу)
PG(ax, [(6, OY1), (-34, OY1 - 8), (-34, OY1 - 4), (6, OY1 + 4)], STEEL, z=4)
# капельник по нижней кромке проёма
PG(ax, [(6, OY0), (-8, OY0 - 3), (-8, OY0 - 12), (-5, OY0 - 12), (-5, OY0 - 5), (6, OY0 - 3)], STEEL, z=4)
# закладные шпильки, гайки, уплотнитель
for sy in (20, 320):
    R(ax, 10, sy - 2, 30, 4, "#7d8790", z=4)
    R(ax, 24, sy - 6, 6, 12, "#5b646d", z=6)
for (y0, y1) in ((8, 42), (298, 332)):
    R(ax, 10, y0, 4, y1 - y0, RUBBER, z=4)
# корыто: фланец, верх, дно с уклоном наружу
T = 2.5
R(ax, 14, 8, T, 34, STEEL, z=5)
R(ax, 14, 298, T, 34, STEEL, z=5)
PG(ax, [(14, 300), (96, 300), (96, 302.5), (14, 302.5)], STEEL, z=5)                 # верх ниши
PG(ax, [(14, 40), (82, 50), (82, 52.5), (14, 42.5)], STEEL, z=5)                     # дно ниши, уклон к клиенту
ax.annotate("", xy=(22, 47), xytext=(70, 56), arrowprops=dict(arrowstyle="-|>", color="#3a8fb7", lw=1.3), zorder=6)
ax.text(-20, 85, "вода стекает\nнаружу", fontsize=8, color="#3a8fb7", ha="right", zorder=6)


def px(y):                     # вставная пластина с наклоном: верх уходит внутрь
    return 82 + (y - 52) * 0.055


PG(ax, [(px(52), 52), (px(300), 300), (px(300) + 3, 300), (px(52) + 3, 52)], STEEL_DD, z=6)
# уплотнитель пластины к корыту
for y in (56, 294):
    R(ax, px(y) + 3, y - 3, 3, 6, RUBBER, z=6)
# Vendotek (верх)
vy0, vy1 = 228, 288
PG(ax, [(px(vy0) - 12, vy0), (px(vy1) - 12, vy1), (px(vy1), vy1), (px(vy0), vy0)], DARK, z=7)                # лицевая часть в нише
PG(ax, [(px(vy0) + 3, vy0 + 4), (px(vy1 - 4) + 3, vy1 - 4), (px(vy1 - 4) + 30, vy1 - 4), (px(vy0 + 4) + 30, vy0 + 4)], "#3a3f45", z=7)
ax.text(px(258) + 18, 258, "Vendotek", fontsize=7.5, color="white", ha="center", va="center", rotation=90, zorder=8)
# купюрник (середина): рамка в нише, корпус и кассета за пластиной, опорная полка снизу
by0, by1 = 150, 212
PG(ax, [(px(by0) - 14, by0), (px(by1) - 14, by1), (px(by1), by1), (px(by0), by0)], DARK, z=7)
R(ax, px(178) - 15, 179, 6, 4, "#ff4d4d", ec="none", z=8)                                                      # щель с подсветкой
R(ax, px(by0) + 3, by0 + 4, 105, 54, "#30363d", z=7)
ax.text(px(by0) + 50, 181, "купюрник", fontsize=8, color="white", ha="center", va="center", zorder=8)
R(ax, px(by0) + 108, by0 + 2, 60, 58, "#4b5158", z=7)
ax.text(px(by0) + 138, 181, "кассета", fontsize=8, color="white", ha="center", va="center", zorder=8)
R(ax, px(by0) + 3, by0 - 4, 170, 4, STEEL_DD, z=7)                                                             # опорная полка
R(ax, px(by0) + 160, by0 - 30, 4, 30, STEEL_DD, z=7)
# монетник (низ): лицевая планка в нише, корпус за пластиной; монеты — вниз в ящик; возврат — жёлоб в чашку в дне ниши
cy0, cy1 = 78, 135
PG(ax, [(px(cy0) - 8, cy0), (px(cy1) - 8, cy1), (px(cy1), cy1), (px(cy0), cy0)], DARK, z=7)
R(ax, px(cy0) + 3, cy0 + 2, 46, 52, "#30363d", z=7)
ax.text(px(cy0) + 26, 106, "монетник", fontsize=7.5, color="white", ha="center", va="center", rotation=90, zorder=8)
R(ax, px(cy0) + 12, -38, 60, 46, "#c7b38a", z=6)                                                               # монетоприёмник
ax.text(px(cy0) + 42, -15, "ящик\nдля монет", fontsize=7.5, color=INK, ha="center", va="center", zorder=8)
ax.plot([px(cy0) + 40, px(cy0) + 40], [cy0 + 2, 8], color="#8a6d3b", lw=2, ls="--", zorder=6)
# жёлоб возврата и чашка возврата в дне ниши
ax.plot([px(cy0) + 10, 60, 34], [cy0 + 2, 70, 54], color="#e08a2e", lw=2.4, zorder=8)
PG(ax, [(24, 42), (44, 45), (44, 58), (24, 56)], "#f3e2c7", z=8)
# жгут к основному модулю
ax.plot([px(by0) + 175, 270, 290], [175, 175, 120], color="#8a6dd6", lw=2.2, zorder=6)

label(ax, (-20, OY1 - 5), "козырёк над нишей", (-25, 345), ha="right")
label(ax, (3, 330), "стекло дверцы с вырезом под нишу\n(закалённое — резать до закалки)", (40, 410))
label(ax, (30, 320), "закладные шпильки, гайки,\nуплотнитель — как у основного модуля", (120, 360))
label(ax, (px(250) + 2, 250), "вставная пластина 2 мм, верх внутрь на 10–15°,\nна шпильках через уплотнитель", (150, 310))
label(ax, (px(180) - 12, 205), "щель купюрника — в нише,\nукрыта от струи", (150, 250))
label(ax, (px(by0) + 100, by0 - 4), "опорная полка под купюрник с кассетой", (190, 128))
label(ax, (34, 56), "чашка возврата монет\nв дне ниши", (-20, 10), ha="right")
label(ax, (-6, OY0 - 10), "дно ниши с уклоном наружу\nи капельник", (-20, -50), ha="right")
label(ax, (px(cy0) + 42, -38), "монеты — в ящик под монетником", (150, -60))
label(ax, (280, 150), "жгут к основному модулю:\nRS-232, MDB, импульсы, 24 В", (190, 70))
ax.set_xlim(-185, 330); ax.set_ylim(-95, 430)
ax.set_title("Разрез сбоку: ниша оплаты", fontsize=14, color=INK, fontweight="bold", pad=2)

# ===================================================================== B. Вид спереди (клиент)
ax = B
R(ax, 0, 0, 200, 360, STEEL_DD, z=1)
R(ax, 0, 0, 200, 360, GLASS, z=1.2, alpha=0.35)
FancyR = FancyBboxPatch((30, 30), 140, 290, boxstyle="round,pad=0,rounding_size=8", fc="#7b848d", ec=EDGE, lw=1.4, zorder=2)
ax.add_patch(FancyR)
ax.add_patch(FancyBboxPatch((38, 38), 124, 274, boxstyle="round,pad=0,rounding_size=6", fc=STEEL, ec=EDGE, lw=1, zorder=3))
PG(ax, [(26, 322), (174, 322), (182, 334), (18, 334)], STEEL, z=4)                     # козырёк
ax.add_patch(FancyBboxPatch((62, 228), 76, 72, boxstyle="round,pad=0,rounding_size=6", fc=DARK, ec=EDGE, lw=1, zorder=4))
R(ax, 70, 236, 60, 50, "#f2f4f6", z=5)
ax.text(100, 270, "БАНКОВСКАЯ\nКАРТА", fontsize=6, color=INK, ha="center", va="center", zorder=6)
ax.text(100, 247, "QR", fontsize=8, color="#2a5bd7", ha="center", va="center", fontweight="bold", zorder=6)
ax.add_patch(FancyBboxPatch((56, 150), 88, 58, boxstyle="round,pad=0,rounding_size=4", fc=DARK, ec=EDGE, lw=1, zorder=4))
R(ax, 66, 186, 68, 6, "#ff4d4d", ec="none", z=5)
ax.text(100, 168, "купюрник", fontsize=7, color="#cfd4d9", ha="center", zorder=5)
R(ax, 72, 76, 56, 58, DARK, z=4)
R(ax, 96, 118, 8, 12, "#c9ced4", z=5)
R(ax, 92, 86, 16, 20, "#f0ece2", z=5)
ax.text(100, 70, "монетник (опция)", fontsize=6.5, color=INK, ha="center", zorder=5)
PG(ax, [(84, 42), (116, 42), (112, 56), (88, 56)], "#f3e2c7", z=5)
ax.text(100, 48, "возврат", fontsize=5.5, color=INK, ha="center", va="center", zorder=6)
ax.set_xlim(-10, 210); ax.set_ylim(-10, 345)
ax.set_title("Вид спереди, со стороны клиента", fontsize=12, color=INK, fontweight="bold", pad=2)

# ===================================================================== C. Две вставные пластины
ax = C


def plate(ox, title, coin):
    R(ax, ox, 0, 110, 230, STEEL, z=2)
    for (x, y) in ((8, 8), (102, 8), (8, 222), (102, 222), (8, 115), (102, 115)):
        ax.add_patch(Circle((ox + x, y), 2.6, fc="white", ec=EDGE, lw=0.8, zorder=3))
    R(ax, ox + 25, 160, 60, 52, "white", z=3)        # Vendotek
    R(ax, ox + 18, 105, 74, 34, "white", z=3)        # купюрник
    if coin:
        R(ax, ox + 30, 30, 50, 50, "white", z=3)
    else:
        R(ax, ox + 30, 30, 50, 50, STEEL_DD, z=3)
        for (x, y) in ((34, 34), (76, 34), (34, 76), (76, 76)):
            ax.add_patch(Circle((ox + x, y), 1.8, fc="#5b646d", ec="none", zorder=4))
        ax.text(ox + 55, 55, "заглушка", fontsize=7, color=INK, ha="center", va="center", zorder=4)
    ax.text(ox + 55, -16, title, fontsize=8.5, color=INK, ha="center", va="center")


plate(0, "с монетником", True)
plate(130, "без монетника", False)
ax.text(120, 258, "Корыто и дверца одни и те же —\nменяется только пластина", fontsize=9, color=INK, ha="center")
ax.set_xlim(-10, 250); ax.set_ylim(-30, 285)
ax.set_title("Вставная пластина — два варианта", fontsize=12, color=INK, fontweight="bold", pad=2)

# ===================================================================== D. Порядок сборки
ax = D
steps = ["Приборы —\nна вставную пластину", "Пластина — в корыто\nчерез уплотнитель", "Полка под купюрник,\nящик для монет, жёлоб",
         "Модуль — на шпильки\nдверцы, гайки", "Жгут — к основному\nмодулю, заземление"]
for i, t in enumerate(steps):
    x = i * 235
    ax.add_patch(FancyBboxPatch((x, 0), 212, 70, boxstyle="round,pad=0,rounding_size=10", fc="#f3eef2", ec="#c9b3c4", lw=1, zorder=2))
    ax.add_patch(Circle((x + 22, 35), 14, fc="#5e2252", ec="none", zorder=3))
    ax.text(x + 22, 35, str(i + 1), color="white", fontsize=11, fontweight="bold", ha="center", va="center", zorder=4)
    ax.text(x + 40, 35, t, fontsize=7.9, color=INK, va="center", zorder=4, linespacing=1.25)
    if i < 4:
        ax.annotate("", xy=(x + 233, 35), xytext=(x + 214, 35), arrowprops=dict(arrowstyle="-|>", color="#9aa2ab", lw=1.3))
ax.set_xlim(-5, 5 * 235); ax.set_ylim(-5, 95)
ax.text(0, 88, "Порядок сборки", fontsize=12, color=INK, fontweight="bold")

fig.text(0.5, 0.008, "Схематичный эскиз модуля оплаты МСО74, без размеров и масштаба", ha="center", fontsize=9.5, color="#7a838c")
fig.savefig(OUT, dpi=140, facecolor="white")
print(OUT)
