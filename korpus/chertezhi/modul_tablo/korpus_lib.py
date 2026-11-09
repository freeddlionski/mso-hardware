"""Общая часть чертежей корпуса МСО74: деталь, DXF R12, рисование, размеры."""
import math
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Arc, Circle, FancyBboxPatch, Polygon, Rectangle

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
        self.poly = None    # свой контур [(x, y), ...] вместо прямоугольника (вырубка углов под гибку)

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

    if part.poly:
        ls, ars = [(part.poly[i], part.poly[(i + 1) % len(part.poly)]) for i in range(len(part.poly))], []
    else:
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


# ============================================================ рисование
def draw_part(ax, p, ox=0, oy=0, show_studs=True):
    if p.poly:
        ax.add_patch(Polygon([(ox + x, oy + y) for x, y in p.poly], closed=True, fc="#eef1f4", ec=CUT, lw=1.1, zorder=2))
    else:
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
    ax.set_title(f"{p.key.split('_')[0]}. {p.title}" + (f" — {p.qty} шт." if p.qty > 1 and "шт" not in p.title else ""), fontsize=10.5,
                 color=INK, fontweight="bold", loc="left", pad=4)
    pad = max(p.w, p.h) * 0.12 + 14
    ax.set_xlim(-pad, p.w + 10); ax.set_ylim(-pad, p.h + 8)
    if show_table:
        rows = features_table(p) + (textwrap.wrap(f"Примечание: {p.note}", 58) if p.note else [])
        ax.text(p.w + 14, p.h, "\n".join(rows[:40]), fontsize=7.2, color=INK, va="top", linespacing=1.35)
        ax.set_xlim(-pad, p.w + 10 + p.w * 0.95)
    return ax


