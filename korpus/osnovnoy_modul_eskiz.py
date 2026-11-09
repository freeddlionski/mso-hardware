"""Эскиз основного модуля МСО по схеме Павла (2026-11-07), без размеров:
стекло во всю дверцу, закладные шпильки на дверце, обечайка с лапками внутрь, матрица заподлицо, DIN за матрицей, накладные касса и кнопка."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle, FancyBboxPatch

OUT = sys.argv[1]
plt.rcParams["font.family"] = "DejaVu Sans"
STEEL, STEEL_D, STEEL_DD, EDGE, INK = "#d9dde1", "#b7bdc4", "#9aa2ab", "#4a5560", "#2b3138"
GLASS, RUBBER, MATRIX, LED = "#9fd3e6", "#2f3338", "#15191e", "#3fd7b6"


def R(ax, x, y, w, h, fc, ec=EDGE, lw=1.1, z=2, alpha=1.0, hatch=None):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha, hatch=hatch))


def label(ax, xy, text, xytext, ha="left"):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=10, color=INK, ha=ha, va="center", zorder=50, linespacing=1.25,
                arrowprops=dict(arrowstyle="-", color="#6b7580", lw=0.9, shrinkA=2, shrinkB=1))


fig, (A, B) = plt.subplots(1, 2, figsize=(18.5, 9), gridspec_kw={"width_ratios": [1.05, 1]})
for ax in (A, B):
    ax.set_aspect("equal"); ax.axis("off")
fig.patch.set_facecolor("white")

# ======================================================================= A. Разрез сбоку
ax = A
# клиент слева, шкаф справа; x — глубина, y — высота
Y0, Y1 = -30, 250            # дверца по высоте (условно)
OY0, OY1 = 45, 175           # проём в дверце под экран
# стекло во всю дверцу (снаружи), вклеено
R(ax, 0, Y0, 7, Y1 - Y0, GLASS, z=3, alpha=0.85)
# стальная дверца с проёмом
R(ax, 7, Y0, 4, OY0 - Y0, STEEL_DD, z=3)
R(ax, 7, OY1, 4, Y1 - OY1, STEEL_DD, z=3)
ax.text(-6, Y1 + 8, "клиент", fontsize=10, color="#6b7580", ha="left")
ax.text(205, Y1 + 8, "шкаф", fontsize=10, color="#6b7580", ha="right")
# закладные шпильки (вварены в дверцу до монтажа стекла), гайки
for sy in (30, 190):
    R(ax, 11, sy - 2, 34, 4, "#7d8790", z=4)
    for k in range(6):
        ax.plot([14 + k * 5, 16 + k * 5], [sy - 2, sy + 2], color="#5b646d", lw=0.7, zorder=5)
    R(ax, 27, sy - 6, 6, 12, "#5b646d", z=6)               # гайка
# уплотнитель между дверцей и фланцем обечайки
for (y0, y1) in ((20, 46), (174, 200)):
    R(ax, 11, y0, 4, y1 - y0, RUBBER, z=4)
# обечайка: фланец (отгиб наружу) + стенки + лапки внутрь
T = 2.5
R(ax, 15, 20, T, 27, STEEL, z=5)                          # фланец низ
R(ax, 15, 173, T, 27, STEEL, z=5)                         # фланец верх
R(ax, 15, 44, 170, T, STEEL, z=5)                         # стенка низ
R(ax, 15, 173.5, 170, T, STEEL, z=5)                      # стенка верх
R(ax, 31, 46.5, T, 9, STEEL, z=5)                         # лапка внутрь (низ)
R(ax, 31, 164.5, T, 9, STEEL, z=5)                        # лапка внутрь (верх)
# матрица заподлицо с фронтом обечайки, упирается в лапки, винты
R(ax, 17.5, 50, 13.5, 120, MATRIX, z=6)
for i in range(13):
    ax.add_patch(Circle((18.6, 56 + i * 9), 1.0, fc=LED, ec="none", zorder=7))
for sy in (51, 169):
    ax.plot([30, 37], [sy, sy], color="#3a3f45", lw=2, zorder=7)          # винт через лапку в стойку матрицы
# лента HUB75 и питание матрицы
ax.plot([31, 52, 60], [110, 112, 128], color="#8a6dd6", lw=2.2, zorder=6)
# DIN-рейка, приварена к обечайке
R(ax, 62, 98, 6, 44, "#c0c6cc", z=6)
ax.plot([60, 62], [98, 98], color=EDGE, lw=1); ax.plot([60, 62], [142, 142], color=EDGE, lw=1)
# модули на DIN (смотрят в сторону шкафа)
mods = [("ESP32-S3", "#203a2e", 62, 30), ("Slave 1", "#23272c", 30, 28), ("24→5 В", "#7a838c", 8, 22), ("HUB75→\nклеммы", "#3a3f45", 150, 24)]
yy = [60, 95, 128, 150]
R(ax, 68, 52, 62, 30, "#203a2e", z=6); ax.text(99, 67, "ESP32-S3 (A147)", fontsize=7.5, color="#c9e9d9", ha="center", va="center", zorder=7)
R(ax, 68, 86, 58, 28, "#23272c", z=6); ax.text(97, 100, "Slave 1 кнопки", fontsize=7.5, color="#dfe3e7", ha="center", va="center", zorder=7)
R(ax, 68, 118, 70, 20, "#7a838c", z=6); ax.text(103, 128, "БП 24→5 В", fontsize=7.5, color="white", ha="center", va="center", zorder=7)
R(ax, 68, 142, 50, 24, "#3a3f45", z=6); ax.text(93, 154, "HUB75→клеммы", fontsize=7, color="white", ha="center", va="center", zorder=7)
# задняя крышка на винтах + накладные касса и кнопка
R(ax, 185, 41, T, 138, STEEL, z=5)
for sy in (48, 110, 172):
    ax.plot([181, 193], [sy, sy], color="#3a3f45", lw=2, zorder=6)
R(ax, 187.5, 70, 10, 26, "#1d2126", z=6)
ax.text(203, 83, "8888", fontsize=8, color="#ff3b30", fontweight="bold", va="center", rotation=90, zorder=7)
R(ax, 187.5, 125, 7, 18, "#c9ced4", z=6)
# сальник снизу
R(ax, 120, 37, 14, 7, "#30363d", z=6)
ax.plot([127, 127, 140], [37, 15, 0], color="#333", lw=2, zorder=5)

label(ax, (3, 230), "стекло (или поликарбонат) во всю дверцу,\nвклеено снаружи", (-10, 285))
label(ax, (9, 0), "стальная дверца с проёмом под экран", (-10, -60))
label(ax, (38, 190), "закладные шпильки: вварены в дверцу\nдо монтажа стекла; модуль — на гайках", (95, 232))
label(ax, (13, 30), "уплотнитель / герметик", (60, -10))
label(ax, (33, 52), "лапки обечайки внутрь —\nупор и винты экрана", (60, 20))
label(ax, (22, 165), "матрица заподлицо с обечайкой,\nзаводится со стороны клиента", (95, 200))
label(ax, (65, 140), "DIN-рейка, приварена к обечайке", (215, 160))
label(ax, (186, 160), "задняя крышка на винтах", (215, 185))
label(ax, (198, 83), "табло кассы — накладное", (215, 70))
label(ax, (195, 134), "кнопка настройки / инкассация", (215, 120))
label(ax, (130, 40), "ввод кабелей снизу", (215, 25))
ax.set_xlim(-20, 330); ax.set_ylim(-80, 300)
ax.set_title("Разрез сбоку: дверца и модуль", fontsize=14, color=INK, fontweight="bold", pad=4)

# ======================================================================= B. Порядок сборки
ax = B


def proj(x, y, z): return (x + z * 0.45, y + z * 0.32)


def P(pts): return [proj(*p) for p in pts]


def poly(pts, fc, z=2, ec=EDGE, lw=1.1, alpha=1.0):
    ax.add_patch(Polygon(P(pts), closed=True, fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha))


def shell(ox, oy, w=150, h=95, d=60, back=False):
    # обечайка: видна передняя рамка (заподлицо), верх и правый бок
    poly([(ox, oy + h, 0), (ox + w, oy + h, 0), (ox + w, oy + h, d), (ox, oy + h, d)], "#e8ebee", 2)
    poly([(ox + w, oy, 0), (ox + w, oy, d), (ox + w, oy + h, d), (ox + w, oy + h, 0)], STEEL_D, 2)
    poly([(ox, oy, 0), (ox + w, oy, 0), (ox + w, oy + h, 0), (ox, oy + h, 0)], STEEL, 2.1)
    poly([(ox + 6, oy + 6, 0), (ox + w - 6, oy + 6, 0), (ox + w - 6, oy + h - 6, 0), (ox + 6, oy + h - 6, 0)], "#f4f6f8", 2.2)
    for (x, y) in ((ox + 10, oy + 10), (ox + w - 10, oy + 10), (ox + 10, oy + h - 10), (ox + w - 10, oy + h - 10)):
        poly([(x - 5, y - 3, 0), (x + 5, y - 3, 0), (x + 5, y + 3, 0), (x - 5, y + 3, 0)], STEEL_DD, 2.3)   # лапки
    return ox, oy, w, h


def step(n, ox, oy, title):
    ax.add_patch(Circle((ox - 2, oy - 26), 12, fc="#5e2252", ec="none", zorder=9))
    ax.text(ox - 2, oy - 26, str(n), color="white", fontsize=11, fontweight="bold", ha="center", va="center", zorder=10)
    ax.text(ox + 16, oy - 26, title, fontsize=9.6, color=INK, va="center", zorder=10, linespacing=1.25)


GX, GY = 290, 225
# 1. обечайка с лапками и приваренной DIN-рейкой
ox, oy = 0, 2 * GY
shell(ox, oy)
poly([(ox + 15, oy + 42, 40), (ox + 135, oy + 42, 40), (ox + 135, oy + 52, 40), (ox + 15, oy + 52, 40)], "#c0c6cc", 1.9, alpha=0.9)
step(1, ox, oy, "Обечайка: лапки внутрь,\nDIN-рейка приварена")
# 2. экран со стороны клиента
ox, oy = GX, 2 * GY
shell(ox, oy)
poly([(ox + 6, oy + 6, 0), (ox + 144, oy + 6, 0), (ox + 144, oy + 89, 0), (ox + 6, oy + 89, 0)], MATRIX, 3)
for r in range(6):
    for c in range(14):
        ax.add_patch(Circle(proj(ox + 16 + c * 9.2, oy + 16 + r * 12.5, 0), 1.3, fc=LED, ec="none", zorder=4))
ax.annotate("", xy=proj(ox + 60, oy + 50, 0), xytext=(ox - 30, oy + 30), zorder=8,
            arrowprops=dict(arrowstyle="-|>", color="#5e2252", lw=1.6))
step(2, ox, oy, "Экран заводится со стороны клиента,\nна лапки, винты — заподлицо")
# 3. модули на DIN (вид сзади)
ox, oy = 0, GY
poly([(ox, oy, 0), (ox + 150, oy, 0), (ox + 150, oy + 95, 0), (ox, oy + 95, 0)], STEEL_D, 2)
poly([(ox + 6, oy + 6, 0), (ox + 144, oy + 6, 0), (ox + 144, oy + 89, 0), (ox + 6, oy + 89, 0)], "#3a3f45", 2.1)
poly([(ox + 8, oy + 40, 0), (ox + 142, oy + 40, 0), (ox + 142, oy + 52, 0), (ox + 8, oy + 52, 0)], "#c0c6cc", 2.2)
for (x, w, c, t) in ((12, 34, "#203a2e", "ESP32"), (50, 34, "#23272c", "Slave 1"), (88, 14, "#7a838c", ""), (106, 34, "#4b5158", "HUB75")):
    poly([(ox + x, oy + 22, 0), (ox + x + w, oy + 22, 0), (ox + x + w, oy + 72, 0), (ox + x, oy + 72, 0)], c, 2.4)
    if t:
        ax.text(*proj(ox + x + w / 2, oy + 47, 0), t, fontsize=7, color="white", ha="center", va="center", rotation=90, zorder=3)
ax.text(*proj(ox + 95, oy + 47, 0), "БП", fontsize=6.5, color="white", ha="center", va="center", rotation=90, zorder=3)
step(3, ox, oy, "На DIN (сзади): ESP32, Slave 1,\nБП 24→5 В, переходник HUB75→клеммы")
# 4. задняя крышка с накладными кассой и кнопкой
ox, oy = GX, GY
poly([(ox, oy, 0), (ox + 150, oy, 0), (ox + 150, oy + 95, 0), (ox, oy + 95, 0)], STEEL, 2)
for (x, y) in ((8, 8), (75, 8), (142, 8), (8, 87), (75, 87), (142, 87), (8, 47), (142, 47)):
    ax.add_patch(Circle(proj(ox + x, oy + y, 0), 2.6, fc="#f4f6f8", ec=EDGE, lw=0.8, zorder=3))
ax.add_patch(FancyBboxPatch(proj(ox + 22, oy + 30, 0), 52, 18, boxstyle="round,pad=0,rounding_size=2", fc="#1d2126", ec=EDGE, lw=1, zorder=3))
ax.text(*proj(ox + 48, oy + 39, 0), "8888", fontsize=9, color="#ff3b30", fontweight="bold", ha="center", va="center", zorder=4)
ax.text(*proj(ox + 48, oy + 60, 0), "КАССА", fontsize=8, color=INK, ha="center", fontweight="bold", zorder=4)
ax.add_patch(Circle(proj(ox + 112, oy + 39, 0), 9, fc="#c9ced4", ec=EDGE, lw=1, zorder=3))
ax.text(*proj(ox + 112, oy + 60, 0), "НАСТРОЙКИ", fontsize=8, color=INK, ha="center", fontweight="bold", zorder=4)
step(4, ox, oy, "Задняя крышка на винтах:\nкасса и кнопка — накладные")
# 5. модуль на шпильки дверцы
ox, oy = 0, 0
poly([(ox - 10, oy - 10, 0), (ox + 440, oy - 10, 0), (ox + 440, oy + 120, 0), (ox - 10, oy + 120, 0)], GLASS, 1.5, alpha=0.6)
poly([(ox + 140, oy + 15, 0), (ox + 300, oy + 15, 0), (ox + 300, oy + 100, 0), (ox + 140, oy + 100, 0)], "white", 1.6)
for (x, y) in ((128, 6), (312, 6), (128, 110), (312, 110), (220, 6), (220, 110)):
    ax.add_patch(Circle((ox + x, oy + y), 4, fc="#7d8790", ec=EDGE, lw=0.9, zorder=2))
ax.text(ox + 30, oy + 60, "дверца\n(стекло во всю\nдверцу снаружи)", fontsize=8.5, color="#3e6d7e", va="center", zorder=3)
ax.text(ox + 220, oy + 57, "проём\nпод экран", fontsize=8.5, color="#6b7580", ha="center", va="center", zorder=3)
ax.text(ox + 335, oy + 60, "шпильки вварены\nдо стекла; модуль —\nчерез уплотнитель,\nна гайки", fontsize=8.5, color=INK, va="center", zorder=3)
step(5, ox, oy, "Модуль на закладные шпильки дверцы через уплотнитель, гайки изнутри")

ax.set_xlim(-50, 470); ax.set_ylim(-50, 2 * GY + 150)
ax.set_title("Порядок сборки", fontsize=14, color=INK, fontweight="bold", pad=4)

fig.text(0.5, 0.012, "Схематичный эскиз основного модуля МСО74 по схеме Павла, без размеров и масштаба", ha="center", fontsize=9.5, color="#7a838c")
plt.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT, dpi=150, facecolor="white")
print(OUT)
