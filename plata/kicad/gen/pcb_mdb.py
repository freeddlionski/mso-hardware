"""MDB по стандарту (18.11.2026): правка готовой платы по новой схеме, трассировка только изменённых связей.
19.11.2026, проход 15: Q11 → PBSS5540X (SOT-89), D17/D21 → BAT46WJ (SOD-323F), F6 → 1812, R64 → 1206, D50 (новый) —
детали из RELAYOUT ставятся заново по placement.json (старая снимается вместе с медью на её площадках); медь цепей
RIP снимается и разводится заново; у F3 переходы выведены из площадок (F3_ADD / F3_REMOVE).

Шаги (mdb.yml); снятие меди и деталей — в eco_text.py (текст файла), здесь — только то, что pcbnew делает надёжно:
  python3 pcb_mdb.py prepare BOARD NETLIST.net PLACEMENT.json ECO.json — новые цепи и детали, значения, LCSC/MPN, цепи
                                                                       площадок по нетлисту; список правок → ECO.json
  python3 eco_text.py clean BOARD ECO.json                             — снять детали и медь (текст)
  python3 pcb_mdb.py export  BOARD ECO.json SNAP.json DSN              — закрепить всю медь, кроме цепей правки в зоне
                                                                       правки; снимок закреплённой; Specctra только
                                                                       для цепей MDB и +5V (прочие — препятствия)
  Freerouting → pcb_route.py import
  python3 pcb_mdb.py check   BOARD SNAP.json                           — закреплённая медь на месте, иначе ошибка
  python3 eco_text.py prune  BOARD ECO.json                            — висящие концы цепей правки (текст)
  python3 pcb_mdb.py finish  BOARD                                     — переходы GND у новых деталей, снять
                                                                       закрепление, перезалить зоны

Объекты, созданные в Python и добавленные на плату, передаются плате (thisown = False): иначе сборщик мусора Python
удаляет их, пока плата ими пользуется.
"""
import json
import math
import sys

import pcbnew

import netlist
import pcb_build
import pcb_route

MM = pcbnew.FromMM
REGION = (140.0, 108.0, 190.0, 146.0)   # зона правки на листе, мм: x0, y0, x1, y1 (19.11: до F6 и J10)
GND_VIA = (0.6, 0.3)                     # переход на плоскость GND: диаметр, сверло, мм
# детали этого прохода (переходы GND — только им; у Q10/U24 переходы уже есть с 18.11)
NEW_REFS = ('Q11', 'Q12', 'R120', 'D17', 'D21', 'R64', 'F6', 'D50')
# поставить заново по placement.json: смена корпуса (Q11, D17, D21, F6, R64) или место под SOT-89 (Q12, R120)
RELAYOUT = ('Q11', 'Q12', 'R120', 'D17', 'D21', 'R64', 'F6')
M = '/MDB и входы/'
EXTRA = ('BI_K',)        # не MDB, но разводится заново: проходит под новым местом R64
# медь, которую снять перед трассировкой: [цепь, рамка x0, y0, x1, y1]
RIP = [[M + n, REGION] for n in ('MDB_TX_NC', 'MDB_TX_QB', 'MDB_TX_E', 'MDB_TX_C', 'MDB_TX_D', 'MDB_TX_P',
                                 'MDB_TX_L', 'MDBRX_K', 'MDBRX_N', 'MDBRX_P')] + [[M + 'BI_K', (155.0, 131.0, 163.0, 140.0)]]
# F3 (2920): переход +24V_P был в площадке F3.1, у F3.2 — один переход и перемычка 0,6 мм (аудит, проход 15, п. 3в)
F3_REMOVE = [('via', '+24V_P', (157.62, 118.6)),
             ('seg', 'MDB_24V', (164.1105, 118.6), (162.798, 118.6)),
             ('seg', 'MDB_24V', (164.11, 118.6), (164.1105, 118.6))]
F3_ADD = [('via', '+24V_P', (156.82, 115.2)), ('via', '+24V_P', (157.62, 115.2)), ('via', '+24V_P', (157.62, 114.4)),
          ('seg', '+24V_P', 'F.Cu', 1.0, (156.82, 115.2), (157.62, 115.2)),
          ('seg', '+24V_P', 'F.Cu', 1.5, (157.62, 114.4), (157.62, 116.6)),
          ('seg', '+24V_P', 'B.Cu', 1.0, (156.82, 115.2), (157.62, 115.2)),
          ('via', 'MDB_24V', (162.294, 117.978)), ('via', 'MDB_24V', (161.79, 117.36)),
          ('seg', 'MDB_24V', 'F.Cu', 1.0, (161.79, 117.36), (162.294, 117.978)),
          ('seg', 'MDB_24V', 'F.Cu', 1.0, (162.294, 117.978), (162.798, 118.6)),
          ('seg', 'MDB_24V', 'F.Cu', 1.0, (162.798, 118.6), (164.11, 118.6)),
          # по B.Cu — поверх прежней дорожки к R10, чтобы переходы были концами отрезков (иначе eco_text сочтёт висящими)
          ('seg', 'MDB_24V', 'B.Cu', 1.0, (162.798, 118.6), (162.294, 117.978)),
          ('seg', 'MDB_24V', 'B.Cu', 1.0, (162.294, 117.978), (161.79, 117.36))]
# запретные для Freerouting зоны (только в DSN): площадки F3 + 0,4 мм — Freerouting не держит зазор 0,3 мм класса P24
KEEPOUT_REFS = ('F3',)
KEEPOUT_GROW = 0.4


def WANTED(net):
    """Цепи, которые разводит Freerouting: цепи MDB и +5V. Остальные для него — препятствия без цепи."""
    leaf = net.rsplit('/', 1)[-1]
    # MDB_24V и LED_MDB_24V — силовые (класс P24), их медь не трогаем (проход 15: Freerouting переукладывал MDB_24V)
    return leaf.startswith(('MDB_TX', 'MDB_RX', 'MDBRX')) or leaf == '+5V' or leaf in EXTRA


def key(t):
    if isinstance(t, pcbnew.PCB_VIA):
        p = t.GetPosition()
        return ['via', round(pcbnew.ToMM(p.x), 3), round(pcbnew.ToMM(p.y), 3), t.GetNetname()]
    a, b = t.GetStart(), t.GetEnd()
    ends = sorted([[round(pcbnew.ToMM(a.x), 3), round(pcbnew.ToMM(a.y), 3)],
                   [round(pcbnew.ToMM(b.x), 3), round(pcbnew.ToMM(b.y), 3)]])
    return ['seg', ends[0], ends[1], round(pcbnew.ToMM(t.GetWidth()), 3), t.GetLayer(), t.GetNetname()]


def raw(t):
    """Всё, чтобы вернуть элемент меди точно (нм)."""
    if isinstance(t, pcbnew.PCB_VIA):
        p = t.GetPosition()
        return ['via', int(p.x), int(p.y), int(t.GetWidth(pcbnew.F_Cu)), int(t.GetDrillValue()), t.GetNetname(),
                int(t.TopLayer()), int(t.BottomLayer()), int(t.GetViaType())]
    a, b = t.GetStart(), t.GetEnd()
    return ['seg', int(a.x), int(a.y), int(b.x), int(b.y), int(t.GetWidth()), int(t.GetLayer()), t.GetNetname()]


def prepare(board_path, net_path, placement, eco_path):
    board = pcb_route.load(board_path)
    comps, nets = netlist.read(net_path)
    pl = json.load(open(placement, encoding='utf-8'))
    eco = {'nets': sorted(n for n in nets if n and not n.startswith('unconnected-')),
           'remove_refs': [], 'new_refs': [], 'changed_pads': [], 'touched': ['+5V']}
    for name in eco['nets']:
        if not board.FindNet(name):
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
            ni.thisown = False
            print('новая цепь', name)
    on_board = {f.GetReference(): f for f in board.GetFootprints()}
    for ref in RELAYOUT:                           # старую — под снятие (eco_text.py), новую поставит цикл ниже
        f = on_board.pop(ref, None)
        if f is not None:
            f.SetReference(ref + '_OLD')
            on_board[ref + '_OLD'] = f
            print('поставить заново', ref)
    for ref, c in comps.items():
        f = on_board.get(ref)
        if f is not None and f.GetFPID().GetLibItemName().wx_str() != c.fp.split(':', 1)[-1]:
            raise SystemExit('%s: корпус на плате %s, в схеме %s — добавить в RELAYOUT'
                             % (ref, f.GetFPID().GetLibItemName().wx_str(), c.fp))
    eco['rip'] = RIP
    eco['remove_items'] = F3_REMOVE
    for spec in F3_ADD:
        net = board.FindNet(spec[1])
        if spec[0] == 'via':
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(MM(spec[2][0]), MM(spec[2][1])))   # координаты листа, не раскладки
            try:
                v.SetWidth(MM(0.6))
            except TypeError:
                v.SetWidth(pcbnew.F_Cu, MM(0.6))
            v.SetDrill(MM(0.3))
            v.SetNet(net)
            board.Add(v)
            v.thisown = False
        else:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(MM(spec[4][0]), MM(spec[4][1])))
            t.SetEnd(pcbnew.VECTOR2I(MM(spec[5][0]), MM(spec[5][1])))
            t.SetWidth(MM(spec[3]))
            t.SetLayer(board.GetLayerID(spec[2]))
            t.SetNet(net)
            board.Add(t)
            t.thisown = False
    for ref in on_board:
        if ref not in comps and not ref.startswith(('H', 'TP')):
            eco['remove_refs'].append(ref)          # снимет eco_text.py
    for ref, c in comps.items():
        f = on_board.get(ref)
        if f is None:
            x, y, rot = pl['parts'][ref]
            f = pcb_build.load(c.fp)
            f.SetReference(ref)
            f.SetPosition(pcb_build.pt(x, y))
            f.SetOrientationDegrees(rot)
            f.Reference().SetVisible(True)
            f.Value().SetVisible(False)
            board.Add(f)
            f.thisown = False
            on_board[ref] = f
            eco['new_refs'].append(ref)
            print('новая деталь', ref, c.value, c.fp, (x, y, rot))
        try:
            f.SetPath(pcbnew.KIID_PATH(c.path))
        except Exception:
            pass
        if f.GetValue() != c.value:
            print('значение', ref, f.GetValue(), '→', c.value)
            f.SetValue(c.value)
        for k in ('LCSC', 'MPN'):
            v = c.props.get(k, '')
            if not v:
                continue
            fld = next((x for x in f.GetFields() if x.GetName() == k), None)
            if fld is None:
                fld = pcbnew.PCB_FIELD(f, f.GetNextFieldId(), k)
                fld.SetVisible(False)
                fld.SetLayer(pcbnew.F_Fab)
                f.AddField(fld)
                fld.thisown = False
            if fld.GetText() != v:
                print('поле %s %s: %s → %s' % (ref, k, fld.GetText() or '—', v))
                fld.SetText(v)
        if f.IsDNP() != bool(c.dnp):
            f.SetDNP(bool(c.dnp))
        for p in f.Pads():
            want = c.pins.get(p.GetNumber(), '')
            if want.startswith('unconnected-'):
                want = ''
            have = p.GetNetname()
            if want != have:
                if want:
                    p.SetNet(board.FindNet(want))
                else:
                    p.SetNetCode(0)
                if ref not in eco['new_refs']:
                    eco['changed_pads'].append([ref, p.GetNumber(), have, want])
                    print('цепь площадки %s.%s: %s → %s' % (ref, p.GetNumber(), have or '—', want or '—'))
                for n in (have, want):
                    if n and n not in eco['touched']:
                        eco['touched'].append(n)
    json.dump(eco, open(eco_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    pcb_route.save(board, board_path)
    print('снять: %s; новые: %s; площадок со сменой цепи: %d'
          % (' '.join(eco['remove_refs']), ' '.join(eco['new_refs']), len(eco['changed_pads'])))


def export(board_path, eco_path, snap_path, dsn):
    """Закрепить всю медь, кроме цепей правки в зоне правки; снимок закреплённой; Specctra для цепей WANTED."""
    eco = json.load(open(eco_path, encoding='utf-8'))
    touched = {n for n in eco['touched'] if WANTED(n)}
    board = pcb_route.load(board_path)
    x0, y0, x1, y1 = (MM(v) for v in REGION)
    snap, free = [], 0
    for t in board.GetTracks():
        pts = [t.GetPosition()] if isinstance(t, pcbnew.PCB_VIA) else [t.GetStart(), t.GetEnd()]
        if t.GetNetname() in touched and all(x0 <= v.x <= x1 and y0 <= v.y <= y1 for v in pts):
            t.SetLocked(False)
            free += 1
        else:
            t.SetLocked(True)
            snap.append({'key': key(t), 'raw': raw(t)})
    json.dump(snap, open(snap_path, 'w'), ensure_ascii=False)
    print('цепи правки: %s; открыто для переукладки %d, закреплено %d' % (', '.join(sorted(touched)), free, len(snap)))
    # заливки внешних слоёв: незакреплённые — убрать (в памяти), закреплённые — фиксированная медь (как pcb_route.export)
    fixed, outer = [], []
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetLayer() not in (pcbnew.F_Cu, pcbnew.B_Cu):
            continue
        outer.append(z)
        if not z.IsLocked():
            continue
        polys = z.GetFilledPolysList(z.GetLayer())
        for i in range(polys.OutlineCount()):
            chains = [polys.COutline(i)] + [polys.CHole(i, h) for h in range(polys.HoleCount(i))]
            rings = [[(c.CPoint(j).x, c.CPoint(j).y) for j in range(c.PointCount())] for c in chains]
            fixed.append((z.GetNetname(), z.GetLayer(), rings))
    for z in outer:
        board.Remove(z)
    for net, layer, rings in fixed:
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(board.FindNet(net))
        z.SetLocked(True)
        poly = pcbnew.SHAPE_POLY_SET()
        for i, ring in enumerate(rings):
            chain = pcbnew.SHAPE_LINE_CHAIN()
            for x, y in ring:
                chain.Append(x, y)
            chain.SetClosed(True)
            if i == 0:
                poly.AddOutline(chain)
            else:
                poly.AddHole(chain)
        z.SetOutline(poly)
        poly.thisown = False
        board.Add(z)
        z.thisown = False
    kept = set()
    for f in board.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            if n and WANTED(n):
                kept.add(n)
            elif n:
                p.SetNetCode(0)
    for f in board.GetFootprints():
        if f.GetReference() not in KEEPOUT_REFS:
            continue
        for p in f.Pads():
            bb = p.GetBoundingBox()
            g = MM(KEEPOUT_GROW)
            ra = pcbnew.ZONE(board)
            ra.SetIsRuleArea(True)
            ra.SetDoNotAllowTracks(True)
            ra.SetDoNotAllowVias(True)
            ra.SetDoNotAllowCopperPour(False)
            ra.SetDoNotAllowPads(False)
            ra.SetDoNotAllowFootprints(False)
            ra.SetLayerSet(pcbnew.LSET.AllCuMask())
            chain = pcbnew.SHAPE_LINE_CHAIN()
            for x, y in ((bb.GetLeft() - g, bb.GetTop() - g), (bb.GetRight() + g, bb.GetTop() - g),
                         (bb.GetRight() + g, bb.GetBottom() + g), (bb.GetLeft() - g, bb.GetBottom() + g)):
                chain.Append(int(x), int(y))
            chain.SetClosed(True)
            poly = pcbnew.SHAPE_POLY_SET()
            poly.AddOutline(chain)
            ra.SetOutline(poly)
            poly.thisown = False
            board.Add(ra)
            ra.thisown = False
            print('запрет для трассировки у %s.%s' % (f.GetReference(), p.GetNumber()))
    print('Specctra: разводятся %d цепей, площадки прочих — препятствия' % len(kept))
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit('экспорт DSN не удался')
    narrow_5v(dsn)


def narrow_5v(dsn):
    """+5V в классе PWR (0,6 мм) не проходит между SOT-89 Q11 и соседями (проход 15: Freerouting оставил Q12.2 и U24.1
    без питания). Ток веток MDB ≤ 80 мА — для трассировки ширина +5V 0,3 мм; меняется только DSN, правила платы прежние."""
    import re
    txt = open(dsn, encoding='utf-8').read()
    m = re.search(r'\(resolution\s+(\w+)\s+(\d+)\)', txt)
    unit = m.group(1) if m else 'um'
    w = {'um': 300, 'mm': 0.3, 'mil': 11.8}.get(unit, 300)
    out, n = [], 0
    for blk in re.split(r'(?=\(class )', txt):
        if blk.startswith('(class ') and re.search(r'[\s"]\+5V[\s")]', blk.split('(circuit')[0]):
            print('класс +5V в DSN:', ' '.join(blk.split())[:300])
            blk, k = re.subn(r'\(width\s+[\d.]+\)', '(width %s)' % w, blk, count=1)
            n += k
        out.append(blk)
    open(dsn, 'w', encoding='utf-8').write(''.join(out))
    print('ширина +5V для трассировки: %s %s (замен %d)' % (w, unit, n))


def check(board_path, snap_path):
    """Закреплённая медь после трассировки: Freerouting не пишет в результат провода цепей, у которых в экспорте не
    было площадок (они препятствия) — такие возвращаются по снимку точно. Сдвинутым считается только элемент цепи
    трассировки (WANTED) — тогда ошибка."""
    board = pcb_route.load(board_path)
    snap = json.load(open(snap_path))
    now = {json.dumps(key(t)) for t in board.GetTracks()}
    lost = [it for it in snap if json.dumps(it['key']) not in now]
    moved = [it for it in lost if WANTED(it['key'][-1])]
    print('закреплённой меди было %d, нет в результате %d (из них цепей трассировки %d); всего сейчас %d'
          % (len(snap), len(lost), len(moved), len(now)))
    for it in moved[:30]:
        print('   сдвинуто:', it['key'])
    # закреплённые провода Freerouting держит как препятствия, но в SES их не пишет — возвращаем все; пересечения
    # поймает DRC ниже
    for it in lost:
        r = it['raw']
        if r[0] == 'seg':
            if r[1] == r[3] and r[2] == r[4]:
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(r[1], r[2]))
            t.SetEnd(pcbnew.VECTOR2I(r[3], r[4]))
            t.SetWidth(r[5])
            t.SetLayer(r[6])
            t.SetNet(board.FindNet(r[7]))
        else:
            t = pcbnew.PCB_VIA(board)
            t.SetViaType(r[8])
            t.SetPosition(pcbnew.VECTOR2I(r[1], r[2]))
            try:
                t.SetWidth(r[3])
            except TypeError:
                t.SetWidth(pcbnew.F_Cu, r[3])
            t.SetDrill(r[4])
            t.SetLayerPair(r[6], r[7])
            t.SetNet(board.FindNet(r[5]))
        t.SetLocked(True)
        board.Add(t)
        t.thisown = False
    pcb_route.save(board, board_path)
    print('возвращено по снимку:', len(lost))


def _d_pt_seg(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def _d_pt_rect(x, y, r):
    return math.hypot(max(r[0] - x, 0, x - r[2]), max(r[1] - y, 0, y - r[3]))


def _cross(a, b, c, d):
    def o(p, q, s):
        return (q[0] - p[0]) * (s[1] - p[1]) - (q[1] - p[1]) * (s[0] - p[0])
    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def _d_seg_seg(a, b, c, d):
    if _cross(a, b, c, d):
        return 0.0
    return min(_d_pt_seg(a[0], a[1], c[0], c[1], d[0], d[1]), _d_pt_seg(b[0], b[1], c[0], c[1], d[0], d[1]),
               _d_pt_seg(c[0], c[1], a[0], a[1], b[0], b[1]), _d_pt_seg(d[0], d[1], a[0], a[1], b[0], b[1]))


def _d_seg_rect(ax, ay, bx, by, r):
    if (r[0] <= ax <= r[2] and r[1] <= ay <= r[3]) or (r[0] <= bx <= r[2] and r[1] <= by <= r[3]):
        return 0.0
    cs = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    if any(_cross((ax, ay), (bx, by), cs[i], cs[(i + 1) % 4]) for i in range(4)):
        return 0.0
    return min([_d_pt_rect(ax, ay, r), _d_pt_rect(bx, by, r)] + [_d_pt_seg(cx, cy, ax, ay, bx, by) for cx, cy in cs])


def add_gnd_vias(board):
    """Каждой площадке GND новых деталей — свой переход на плоскость In1 рядом, дорожкой 0,3 мм по F.Cu. Место —
    первое из кругов 1,0–2,6 мм вокруг площадки, где переход и дорожка не ближе 0,2 мм к чужой меди и переход
    не под корпусом детали. Геометрия — числами (нм)."""
    clr = MM(0.2)
    rv, drill, hw = MM(GND_VIA[0]) / 2, MM(GND_VIA[1]), MM(0.3) / 2
    gnd = board.FindNet('GND')
    segs, vias = [], []
    for t in board.GetTracks():
        if t.GetNetname() == 'GND':
            continue
        if isinstance(t, pcbnew.PCB_VIA):
            v = t.GetPosition()
            vias.append((v.x, v.y, t.GetWidth(pcbnew.F_Cu) / 2))
        else:
            a, e = t.GetStart(), t.GetEnd()
            segs.append(((a.x, a.y), (e.x, e.y), t.GetWidth() / 2, t.GetLayer()))
    pads, yards, targets = [], [], []
    for f in board.GetFootprints():
        cy = f.GetCourtyard(pcbnew.F_CrtYd)
        if cy.OutlineCount():
            bb = cy.BBox()
            yards.append((bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
        for p in f.Pads():
            bb = p.GetBoundingBox()
            r = (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())
            if p.GetNetname() == 'GND':
                if f.GetReference() in NEW_REFS:
                    c = p.GetPosition()
                    targets.append((f.GetReference(), p.GetNumber(), c.x, c.y))
                continue
            pads.append((r, p.IsOnLayer(pcbnew.F_Cu)))

    def ok(cx, cy, vx, vy):
        if any(r[0] <= vx <= r[2] and r[1] <= vy <= r[3] for r in yards):
            return False
        for a, e, w, L in segs:
            if _d_pt_seg(vx, vy, a[0], a[1], e[0], e[1]) < rv + w + clr:
                return False
            if L == pcbnew.F_Cu and _d_seg_seg((cx, cy), (vx, vy), a, e) < hw + w + clr:
                return False
        for x, y, r in vias:
            if math.hypot(vx - x, vy - y) < rv + r + clr or _d_pt_seg(x, y, cx, cy, vx, vy) < hw + r + clr:
                return False
        for r, onf in pads:
            if _d_pt_rect(vx, vy, r) < rv + clr:
                return False
            if onf and _d_seg_rect(cx, cy, vx, vy, r) < hw + clr:
                return False
        return True

    for ref, num, cx, cy in targets:
        spot = None
        for rr in [x / 10 for x in range(10, 27, 2)]:
            for k in range(16):
                ang = 2 * math.pi * k / 16
                vx, vy = int(cx + MM(rr * math.cos(ang))), int(cy + MM(rr * math.sin(ang)))
                if ok(cx, cy, vx, vy):
                    spot = (vx, vy)
                    break
            if spot:
                break
        if not spot:
            raise SystemExit('нет места для перехода GND у %s.%s' % (ref, num))
        v = pcbnew.VECTOR2I(spot[0], spot[1])
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(v)
        try:
            via.SetWidth(int(2 * rv))
        except TypeError:
            via.SetWidth(pcbnew.F_Cu, int(2 * rv))
        via.SetDrill(drill)
        via.SetNet(gnd)
        board.Add(via)
        via.thisown = False
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(pcbnew.VECTOR2I(cx, cy))
        tr.SetEnd(v)
        tr.SetWidth(MM(0.3))
        tr.SetLayer(pcbnew.F_Cu)
        tr.SetNet(gnd)
        board.Add(tr)
        tr.thisown = False
        vias.append((spot[0], spot[1], rv))
        print('%s.%s → переход GND (%.2f; %.2f)' % (ref, num, pcbnew.ToMM(spot[0]), pcbnew.ToMM(spot[1])))


def finish(board_path):
    board = pcb_route.load(board_path)
    add_gnd_vias(board)
    for t in board.GetTracks():
        t.SetLocked(False)
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcb_route.save(board, board_path)


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    {'prepare': prepare, 'export': export, 'check': check, 'finish': finish}[cmd](*args)
