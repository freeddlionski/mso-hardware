"""Раскладка позиционных обозначений (R1, C5…) на шелкографии готовой платы.

python3 pcb_silk.py BOARD.kicad_pcb  — правит файл на месте.

Для каждого обозначения перебирает места вокруг корпуса (сверху, снизу,
слева, справа, на корпусе) и два размера шрифта; берёт первое место, где
текст не задевает чужую шелкографию, площадки, другие обозначения и край
платы. Если места нет — обозначение скрывается на шелкографии (остаётся
на слое Fab, в сборочном PDF и в файле координат). Медь и детали не
трогаются.
"""
import sys
import pcbnew
import pcb_route

MM = pcbnew.FromMM
SIZES = ((1.0, 0.15), (0.8, 0.15))   # высота, толщина линии, мм (JLC: ≥0.8 / ≥0.15)
GAP_SILK = MM(0.1)                   # зазор до чужой шелкографии
GAP_PAD = MM(0.2)                    # до площадки: 0,05 маска + ~0,15 запас
GAP_EDGE = MM(0.4)


def rect(b, grow=0):
    return (b.GetLeft() - grow, b.GetTop() - grow, b.GetRight() + grow, b.GetBottom() + grow)


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def main(path):
    board = pcb_route.load(path)
    edge = rect(board.GetBoardEdgesBoundingBox(), -GAP_EDGE)
    sides = {pcbnew.F_SilkS: pcbnew.F_Cu, pcbnew.B_SilkS: pcbnew.B_Cu}
    silk = {l: [] for l in sides}        # (bbox, ref владельца)
    pads = {l: [] for l in sides}
    fps = list(board.GetFootprints())
    for fp in fps:
        r = fp.GetReference()
        for g in fp.GraphicalItems():
            if g.GetLayer() in silk and g.GetClass() != 'PCB_TEXT':
                silk[g.GetLayer()].append((rect(g.GetBoundingBox(), GAP_SILK), r))
        for p in fp.Pads():
            for sl, cu in sides.items():
                if p.IsOnLayer(cu) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    pads[sl].append(rect(p.GetBoundingBox(), GAP_PAD))
    for d in board.GetDrawings():
        if d.GetLayer() in silk:
            silk[d.GetLayer()].append((rect(d.GetBoundingBox(), GAP_SILK), None))
    placed = {l: [] for l in sides}
    kept = hidden = 0
    # Крупные корпуса первыми — у них меньше вариантов.
    fps.sort(key=lambda f: -f.GetCourtyard(f.GetLayer() == pcbnew.B_Cu and pcbnew.B_CrtYd
                                           or pcbnew.F_CrtYd).BBox().GetArea())
    for fp in fps:
        t = fp.Reference()
        sl = t.GetLayer()
        if sl not in sides or not t.IsVisible():
            continue
        own = [b for b, r in silk[sl] if r == fp.GetReference()]
        body = fp.GetBoundingBox(False)
        cx, cy = body.GetCenter().x, body.GetCenter().y
        best = None
        for h, w in SIZES:
            t.SetTextSize(pcbnew.VECTOR2I(MM(h), MM(h)))
            t.SetTextThickness(MM(w))
            for rot in (0, 90):
                t.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
                tb = t.GetBoundingBox()
                hw, hh = tb.GetWidth() // 2, tb.GetHeight() // 2
                m = MM(0.15)
                cand = [(cx, body.GetTop() - hh - m), (cx, body.GetBottom() + hh + m),
                        (body.GetLeft() - hw - m, cy), (body.GetRight() + hw + m, cy),
                        (cx, cy)]
                for x, y in cand:
                    t.SetTextPos(pcbnew.VECTOR2I(int(x), int(y)))
                    b = rect(t.GetBoundingBox())
                    if not (edge[0] <= b[0] and b[2] <= edge[2] and edge[1] <= b[1] and b[3] <= edge[3]):
                        continue
                    others = [s for s, r in silk[sl] if r != fp.GetReference()]
                    if (x, y) == (cx, cy):
                        others += own            # на корпусе — не по своему контуру
                    if any(hit(b, o) for o in others) or any(hit(b, p) for p in pads[sl]) \
                            or any(hit(b, o) for o in placed[sl]):
                        continue
                    best = (h, w, rot, x, y, b)
                    break
                if best:
                    break
            if best:
                break
        if best:
            h, w, rot, x, y, b = best
            t.SetTextSize(pcbnew.VECTOR2I(MM(h), MM(h)))
            t.SetTextThickness(MM(w))
            t.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
            t.SetTextPos(pcbnew.VECTOR2I(int(x), int(y)))
            placed[sl].append(b)
            kept += 1
        else:
            t.SetVisible(False)
            hidden += 1
    pcb_route.save(board, path)
    print(f'обозначения: на шелкографии {kept}, скрыто {hidden}')


if __name__ == '__main__':
    main(sys.argv[1])
