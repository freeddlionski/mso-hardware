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

# Подписи контактов клемм (номер вывода → текст), как в PINOUT/схеме.
PIN_LABELS = {
    'J1': {'1': '+24V', '2': 'GND'},
    'J2': {'1': '+24V', '2': 'GND'},
    'J9': {'1': 'TXD', '2': 'RXD', '3': 'GND'},
    'J8': {'1': 'A', '2': 'B', '3': 'GND'},
    'J11': {'1': '+12', '2': 'GND', '3': 'ИМП', '4': 'БЛК'},
    'J12': {'1': '+24', '2': '+12', '3': 'GND', '4': 'ИМП'},
    'J13': {'1': 'КН', '2': 'GND'},
    'J15': {'1': '1', '2': '2', '3': '3', '4': '4', '5': 'GND', '6': 'GND'},
    'J16': {'1': '+24', '2': '1', '3': '2', '4': '3', '5': '4', '6': 'GND'},
}
# Подписи контактов сбоку (вертикальные разъёмы табло у левого края): текст справа от вывода.
PIN_SIDE = {'J3': {'1': '+5V', '2': 'GND'}, 'J4': {'1': '+5V', '2': 'GND'}}
# Названия узлов: (текст, сдвиг от центра детали x, y мм) — ищется ближайшее свободное место.
TITLES = {
    'J1': ('ПИТАНИЕ 24В', 0, -9), 'J2': ('VENDOTEK 24В', 0, -9),
    'J9': ('RS-232', 0, -9), 'J8': ('RS-485', 0, -9), 'J10': ('MDB', 0, -8),
    'J11': ('МОНЕТНИК', 0, -9), 'J12': ('КУПЮРНИК', 0, -9), 'J13': ('СЕРВИС', 0, -9),
    'J15': ('ВХОДЫ', 0, -9), 'J16': ('ВЫХОДЫ', 0, -9),
    'J3': ('ТАБЛО 1', 4, -6), 'J4': ('ТАБЛО 2', 4, -6),
    'J7': ('СЕТЬ', -12, 0), 'J18': ('VENDOTEK LAN', -12, 0), 'J5': ('USB', -7, 0),
    'J14': ('HUB75', 0, 5), 'J6': ('UART', 0, -5), 'J17': ('РЕЗЕРВ', 0, -4),
    'JP1': ('120 Ом', 0, -4), 'SW1': ('RESET', 0, 4), 'SW2': ('BOOT', 0, 4), 'SW3': ('СЕРВИС', 0, 4),
}
NAMEPLATE = 'МСО74 · mso74.ru · плата rev A 2026'


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
    drawings = list(board.Drawings())
    for d in drawings:                           # прошлые подписи — заново
        if d.GetClass() == 'PCB_TEXT' and d.GetLayer() in silk:
            board.Remove(d)
        elif d.GetLayer() in silk:
            silk[d.GetLayer()].append((rect(d.GetBoundingBox(), GAP_SILK), None))
    placed = {l: [] for l in sides}
    for fp in fps:
        fp.Reference().SetVisible(True)
    sl = pcbnew.F_SilkS

    byref = {fp.GetReference(): fp for fp in fps}
    court = {}                                   # корпуса деталей: подписи на них не кладём
    for fp in fps:
        c = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        court[fp.GetReference()] = rect(c if c.GetWidth() > 0 else fp.GetBoundingBox(False))

    def free(b, own=None):
        return (edge[0] <= b[0] and b[2] <= edge[2] and edge[1] <= b[1] and b[3] <= edge[3]
                and not any(hit(b, o) for o, _ in silk[sl]) and not any(hit(b, p) for p in pads[sl])
                and not any(hit(b, o) for o in placed[sl])
                and not any(hit(b, c) for r, c in court.items() if r != own))

    def text(s_, h, rot=0):
        t = pcbnew.PCB_TEXT(board)
        t.SetLayer(sl)
        t.SetText(s_)
        t.SetTextSize(pcbnew.VECTOR2I(MM(h), MM(h)))
        t.SetTextThickness(MM(0.15))
        t.SetTextAngle(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        return t

    def at(t, x, y, bottom=False):
        t.SetTextPos(pcbnew.VECTOR2I(MM(x), MM(y)))
        if bottom:
            t.Move(pcbnew.VECTOR2I(0, MM(y) - t.GetBoundingBox().GetBottom()))
        return rect(t.GetBoundingBox())

    def add(t):
        board.Add(t)
        placed[sl].append(rect(t.GetBoundingBox(), GAP_SILK))

    def put(s_, cands, h=1.0, quiet=False):
        for hh in (h, 0.8):
            t = text(s_, hh)
            for x, y in cands:
                if free(at(t, x, y)):
                    add(t)
                    return t
        if not quiet:
            print('нет места для подписи:', s_)
        return None

    def near(ref, dx, dy, r=16):
        c = byref[ref].GetBoundingBox(False).GetCenter()
        x0, y0 = pcbnew.ToMM(c.x) + dx, pcbnew.ToMM(c.y) + dy
        return sorted(((x0 + i * 0.5, y0 + j * 0.5) for i in range(-2 * r, 2 * r + 1) for j in range(-r, r + 1)),
                      key=lambda p: (p[0] - x0) ** 2 + 4 * (p[1] - y0) ** 2)

    def silk_top(fp):
        ys = [g.GetBoundingBox().GetTop() for g in fp.GraphicalItems()
              if g.GetLayer() == sl and g.GetClass() != 'PCB_TEXT']
        return pcbnew.ToMM(min(ys + [court[fp.GetReference()][1]]))

    def pad(fp, n):
        q = [p.GetPosition() for p in fp.Pads() if p.GetNumber() == n][0]
        return pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)

    # Клеммы по нижнему краю: подписи контактов над корпусом, все на одной высоте. Не влезли —
    # строка «НАЗВАНИЕ: контакты слева направо» над разъёмом.
    titled = set()
    for ref, pins in PIN_LABELS.items():
        fp = byref[ref]
        top = silk_top(fp)
        rot = 90 if max(len(v) for v in pins.values()) > 3 else 0
        ts = {n: text(v, 1.0 if rot else 0.9, rot) for n, v in pins.items()}
        done = False
        for k in range(40):
            y = top - 0.3 - k * 0.25
            spots = {}
            for n, t in ts.items():
                x, _ = pad(fp, n)
                for dx in (0, -0.4, 0.4):
                    if free(at(t, x + dx, y, bottom=True), own=ref):
                        spots[n] = x + dx
                        break
                else:
                    break
            if len(spots) == len(ts):
                for n, t in ts.items():
                    at(t, spots[n], y, bottom=True)
                    add(t)
                done = True
                break
        if done:
            continue
        title, dx, dy = TITLES[ref]
        if put(title + ': ' + ' '.join(pins.values()), near(ref, dx, dy + 2), quiet=True):
            titled.add(ref)
        else:
            put(' '.join(pins.values()), near(ref, dx, dy + 3, r=30))
    for ref, pins in PIN_SIDE.items():
        fp = byref[ref]
        right = pcbnew.ToMM(court[ref][2])
        for n, s_ in pins.items():
            _, y = pad(fp, n)
            side = [(right + 1 + k * 0.5, y + dy) for k in range(30) for dy in (0, -1, 1, -2, 2)]
            put(s_, side + near(ref, 0, -5 if n == '1' else 5, r=8))
    # Названия узлов: ближайшее свободное место к точке у детали.
    for ref, (s_, dx, dy) in TITLES.items():
        if ref not in titled:
            put(s_, near(ref, dx, dy, r=30), h=1.2)
    # Шильдик платы — ближе к центру низа.
    b = board.GetBoardEdgesBoundingBox()
    x0, y0 = pcbnew.ToMM(b.GetCenter().x), pcbnew.ToMM(b.GetBottom()) - 30
    cands = sorted(((x0 + 2 * i, y0 + j) for i in range(-55, 56) for j in range(-25, 25)),
                   key=lambda p: (p[0] - x0) ** 2 + (p[1] - y0) ** 2)
    put(NAMEPLATE, cands, h=1.5)
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
