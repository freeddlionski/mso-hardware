"""MDB по стандарту (18.11.2026): правка готовой платы по новой схеме, трассировка только изменённых связей.

  python3 pcb_mdb.py prepare BOARD.kicad_pcb NETLIST.net PLACEMENT.json SNAPSHOT.json — плата ← схема (ECO),
                                                    обрывки сняты, остальная медь закреплена (locked), снимок в SNAPSHOT
  python3 pcb_mdb.py finish  BOARD.kicad_pcb SNAPSHOT.json               — после импорта Freerouting: проверка, что
                                                                           чужая медь не сдвинулась, снять закрепление

Что делает prepare (контейнер kicad/kicad:9.0, pcbnew):
1. Сверяет каждое посадочное место с нетлистом: значение, LCSC/MPN, DNP, цепи площадок. Снимает детали, которых нет
   в схеме (U13, U14, D18), ставит новые (Q10–Q12, R119–R121, U24) по placement.json.
2. Снимает дорожки цепей, которых больше нет, и дорожки, подходившие к площадкам, у которых сменилась цепь или которые
   сняты; дальше — по цепочке висящих концов (только от этих точек; заливки и плоскости не трогает).
3. Закрепляет (locked) все оставшиеся дорожки и переходы: KiCad передаёт их в Specctra как защищённые — Freerouting
   разводит только недостающие связи и чужую медь не двигает. Снимок чужой меди — в SNAPSHOT.json для finish.
"""
import faulthandler
import json
import math
import sys

faulthandler.enable()

import pcbnew

import netlist
import pcb_build
import pcb_route

MM = pcbnew.FromMM
REGION = (140.0, 108.0, 175.0, 142.0)   # зона правки на листе, мм: x0, y0, x1, y1
GND_VIA = (0.6, 0.3)                            # переход на плоскость GND: диаметр, сверло, мм


def to_mm(v):
    return round(pcbnew.ToMM(v), 2)          # 10 мкм: Specctra округляет координаты при обмене


def WANTED(net):
    """Цепи, которые разводит Freerouting: все цепи MDB и +5V. Остальные для него — препятствия без цепи."""
    return 'MDB' in net or net == '+5V'


def seg_raw(t):
    if isinstance(t, pcbnew.PCB_VIA):
        p = t.GetPosition()
        return ['via', p.x, p.y, t.GetWidth(pcbnew.F_Cu), t.GetDrillValue(), t.GetNetname(),
                t.TopLayer(), t.BottomLayer(), int(t.GetViaType())]
    a, b = t.GetStart(), t.GetEnd()
    return ['seg', a.x, a.y, b.x, b.y, t.GetWidth(), t.GetLayer(), t.GetNetname()]


def seg_key(t):
    if isinstance(t, pcbnew.PCB_VIA):
        p = t.GetPosition()
        return ('via', to_mm(p.x), to_mm(p.y), to_mm(t.GetWidth(pcbnew.F_Cu)), t.GetNetname())
    a, b = t.GetStart(), t.GetEnd()
    ends = sorted([(to_mm(a.x), to_mm(a.y)), (to_mm(b.x), to_mm(b.y))])
    return ('seg', ends[0], ends[1], to_mm(t.GetWidth()), t.GetLayer(), t.GetNetname())


def rect(b):
    """Копия рамки как чисел: объекты KiCad, полученные от площадки, могут ссылаться на её внутренности."""
    return (b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom())


def in_rect(r, v, grow=0):
    return r[0] - grow <= v.x <= r[2] + grow and r[1] - grow <= v.y <= r[3] + grow


def touches_point(t, v, r=MM(0.02)):
    if isinstance(t, pcbnew.PCB_VIA):
        return (t.GetPosition() - v).EuclideanNorm() <= t.GetWidth(pcbnew.F_Cu) // 2 + r
    return (t.GetStart() - v).EuclideanNorm() <= r or (t.GetEnd() - v).EuclideanNorm() <= r


def ends_of(t):
    return [t.GetPosition()] if isinstance(t, pcbnew.PCB_VIA) else [t.GetStart(), t.GetEnd()]


def remove_with_ends(board, t, queue):
    """Снять элемент меди и отрезки нулевой длины той же цепи на его концах; концы — в очередь на проверку."""
    net, ends = t.GetNetname(), ends_of(t)
    board.Remove(t)
    n = 1
    for o in list(board.GetTracks()):
        if (not isinstance(o, pcbnew.PCB_VIA) and o.GetNetname() == net and o.GetStart() == o.GetEnd()
                and any(touches_point(o, e) for e in ends)):
            board.Remove(o)
            n += 1
    queue += [(e, net) for e in ends]
    return n


def anchored(board, pos, net, tr):
    """Конец держится: площадка той же цепи, заливка той же цепи, другой элемент меди той же цепи."""
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == net and p.GetEffectiveShape(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu)
                                                            else pcbnew.B_Cu).Collide(pos, 0):
                return True
    via = isinstance(tr, pcbnew.PCB_VIA)
    layers = list(tr.GetLayerSet().CuStack()) if via else [tr.GetLayer()]
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetname() != net:
            continue
        for L in layers:
            if z.IsOnLayer(L) and z.HitTestFilledArea(L, pos):
                return True
    for o in board.GetTracks():
        if o is tr or o.GetNetname() != net:
            continue
        if isinstance(o, pcbnew.PCB_VIA):
            if (o.GetPosition() - pos).EuclideanNorm() <= o.GetWidth(pcbnew.F_Cu) // 2:
                return True
        elif o.GetStart() != o.GetEnd() and (via or o.GetLayer() == tr.GetLayer()):
            if touches_point(o, pos) or o.HitTest(pos, 0):
                return True
    return False


def prune(board, nets=None, queue=None):
    """Висящие концы: отрезок, у которого конец ни на чём не держится, и переход не плоскости, к которому подходит
    не больше одного отрезка. С очередью — только от точек очереди; без неё — по цепям nets на всей плате."""
    planes = ('GND', '+3V3', '+24V_P')
    removed = 0
    while True:
        cand = []
        if queue is not None:
            if not queue:
                break
            pts = queue[:]
            del queue[:]
            for pos, net in pts:
                cand += [t for t in board.GetTracks() if t.GetNetname() == net and touches_point(t, pos)]
        else:
            cand = [t for t in board.GetTracks() if t.GetNetname() in nets]
        changed = False
        seen = set()
        for t in cand:
            if id(t) in seen:
                continue
            seen.add(id(t))
            net = t.GetNetname()
            if isinstance(t, pcbnew.PCB_VIA):
                if any(p.GetNetname() == net and p.GetEffectiveShape(pcbnew.F_Cu).Collide(t.GetPosition(), 0)
                       for f in board.GetFootprints() for p in f.Pads()):
                    continue
                n = sum(1 for o in board.GetTracks() if not isinstance(o, pcbnew.PCB_VIA) and o.GetNetname() == net
                        and o.GetStart() != o.GetEnd() and touches_point(o, t.GetPosition()))
                if n == 0 or (n == 1 and net not in planes):
                    removed += remove_with_ends(board, t, queue if queue is not None else [])
                    changed = True
                continue
            if t.GetStart() == t.GetEnd():
                continue
            if all(anchored(board, e, net, t) for e in ends_of(t)):
                continue
            removed += remove_with_ends(board, t, queue if queue is not None else [])
            changed = True
        if queue is None and not changed:
            break
    return removed


def prepare(board_path, net_path, placement, snapshot):
    board = pcb_route.load(board_path)
    comps, nets = netlist.read(net_path)
    pl = json.load(open(placement, encoding='utf-8'))

    # --- цепи: новые имена ---
    new_nets = set()
    for name in sorted(nets):
        if name and not name.startswith('unconnected-') and not board.FindNet(name):
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
            new_nets.add(name)
            print('новая цепь', name)

    dirty = []          # (точка, имя прежней цепи) — откуда снимать дорожки
    added = []          # новые посадочные места
    on_board = {f.GetReference(): f for f in board.GetFootprints()}
    for ref, f in list(on_board.items()):
        if ref.startswith(('H', 'TP')) and ref not in comps:
            continue                                   # крепёж добавляет pcb_build сам
        if ref in comps:
            continue
        for p in f.Pads():
            if p.GetNetname():
                dirty.append((p.GetPosition(), p.GetNetname(), rect(p.GetBoundingBox())))
        board.Remove(f)
        print('снята деталь', ref)
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
            added.append(f)
            print('новая деталь', ref, c.value, c.fp, (x, y, rot))
        try:
            f.SetPath(pcbnew.KIID_PATH(c.path))
        except Exception:
            pass
        if f.GetValue() != c.value:
            print('значение', ref, f.GetValue(), '→', c.value)
            f.SetValue(c.value)
        for key in ('LCSC', 'MPN'):
            v = c.props.get(key, '')
            if not v:
                continue
            fld = next((x for x in f.GetFields() if x.GetName() == key), None)
            if fld is None:
                fld = pcbnew.PCB_FIELD(f, f.GetNextFieldId(), key)
                fld.SetVisible(False)
                fld.SetLayer(pcbnew.F_Fab)
                f.AddField(fld)
            if fld.GetText() != v:
                print('поле %s %s: %s → %s' % (ref, key, fld.GetText() or '—', v))
                fld.SetText(v)
        if f.IsDNP() != bool(c.dnp):
            f.SetDNP(bool(c.dnp))
        for p in f.Pads():
            want = c.pins.get(p.GetNumber(), '')
            if want.startswith('unconnected-'):
                want = ''
            have = p.GetNetname()
            if want != have:
                if have:
                    dirty.append((p.GetPosition(), have, rect(p.GetBoundingBox())))
                if want:
                    new_nets.add(want)
                if want:
                    p.SetNet(board.FindNet(want))
                else:
                    p.SetNetCode(0)
                print('цепь площадки %s.%s: %s → %s' % (ref, p.GetNumber(), have or '—', want or '—'))

    # --- дорожки: снять цепи, которых нет, и обрывки у изменённых площадок ---
    removed = 0
    # медь чужих цепей под площадками новых деталей (с зазором 0,2 мм) — снять, дальше по цепочке висящих концов
    clr = MM(0.2)
    for f in added:
        for p in f.Pads():
            ps = p.GetEffectiveShape(pcbnew.F_Cu)
            for t in list(board.GetTracks()):
                if t.GetNetname() == p.GetNetname():
                    continue
                if isinstance(t, pcbnew.PCB_VIA):
                    hit = ps.Collide(pcbnew.SHAPE_CIRCLE(t.GetPosition(), t.GetWidth(pcbnew.F_Cu) // 2), clr)
                    ends = [t.GetPosition()]
                else:
                    if t.GetLayer() != pcbnew.F_Cu:
                        continue
                    hit = ps.Collide(pcbnew.SHAPE_SEGMENT(t.GetStart(), t.GetEnd(), t.GetWidth()), clr)
                    ends = [t.GetStart(), t.GetEnd()]
                if hit:
                    print('под %s.%s снято: %s' % (f.GetReference(), p.GetNumber(), seg_key(t)))
                    net = t.GetNetname()
                    board.Remove(t)
                    removed += 1
                    for e in ends:
                        dirty.append((e, net, None))
    for t in list(board.GetTracks()):
        if t.GetNetname() and t.GetNetname() not in nets:
            board.Remove(t)
            removed += 1
    # площадки со сменившейся цепью и снятых деталей: все дорожки прежней цепи, касающиеся их, — снять
    queue = []
    for point, net, shape in dirty:
        if shape is None:
            queue.append((point, net))          # конец снятой чужой меди — только проверка «висит ли»
            continue
        for t in list(board.GetTracks()):
            if t.GetNetname() != net:
                continue
            # shape — копия рамки площадки (BOX2I): форму площадки хранить нельзя — GetEffectiveShape отдаёт ссылку на
            # кэш внутри площадки, после снятия детали она недействительна (падение 139 в прогоне 44379977742)
            if isinstance(t, pcbnew.PCB_VIA):
                hit = in_rect(shape, t.GetPosition(), t.GetWidth(pcbnew.F_Cu) // 2)
            else:
                hit = in_rect(shape, t.GetStart()) or in_rect(shape, t.GetEnd())
            if hit:
                removed += remove_with_ends(board, t, queue)
    removed += prune(board, queue=queue)
    print('снято дорожек и переходов:', removed)

    # --- закрепить всё оставшееся, снимок для проверки после трассировки ---
    touched = {n for _, n, _ in dirty} | new_nets | {p.GetNetname() for f in added for p in f.Pads()}
    touched = {n for n in touched if WANTED(n)}
    print('цепи правки:', ', '.join(sorted(touched)))
    snap = []
    x0, y0, x1, y1 = (MM(v) for v in REGION)
    def inside(v):
        return x0 <= v.x <= x1 and y0 <= v.y <= y1
    free = 0
    for t in board.GetTracks():
        pts = [t.GetPosition()] if isinstance(t, pcbnew.PCB_VIA) else [t.GetStart(), t.GetEnd()]
        if t.GetNetname() in touched and all(inside(v) for v in pts):
            t.SetLocked(False)                      # медь MDB и +5V в зоне правки — можно переложить
            free += 1
            continue
        t.SetLocked(True)
        snap.append({'key': list(seg_key(t)), 'raw': seg_raw(t)})
    print('открыто для переукладки (MDB, +5V в зоне правки):', free)
    json.dump(snap, open(snapshot, 'w'), ensure_ascii=False)
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcb_route.save(board, board_path)
    print('закреплено элементов меди:', len(snap))


def export(board_path, dsn):
    """Specctra только для цепей WANTED: площадки прочих цепей — без цепи (препятствия), вся медь закреплена.
    Незакреплённые заливки внешних слоёв убираются в памяти (как в pcb_route.export), закреплённые — фиксированная медь."""
    board = pcb_route.load(board_path)
    fixed_areas, outer = [], []
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
            fixed_areas.append((z.GetNetname(), z.GetLayer(), rings))
    for z in outer:
        board.Remove(z)
    for net, layer, rings in fixed_areas:
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
    kept, hidden = set(), set()
    for f in board.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            if not n:
                continue
            if WANTED(n):
                kept.add(n)
            else:
                hidden.add(n)
                p.SetNetCode(0)
    print('экспорт: разводятся %d цепей (%s), остальные %d — препятствия'
          % (len(kept), ', '.join(sorted(kept)), len(hidden)))
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit('экспорт DSN не удался')


def finish(board_path, snapshot):
    """После импорта SES: закреплённая медь должна остаться. Пропавшие элементы чужих цепей возвращаются по снимку
    (Freerouting иногда выбрасывает «висящие» для него переходы плоскостей); вырожденные отрезки нулевой длины — нет."""
    board = pcb_route.load(board_path)
    snap = json.load(open(snapshot))
    now = {seg_key(t) for t in board.GetTracks()}
    restored = skipped = 0
    for item in snap:
        key = tuple(tuple(x) if isinstance(x, list) else x for x in item['key'])
        if key in now:
            continue
        r = item['raw']
        if r[0] == 'seg':
            if r[1] == r[3] and r[2] == r[4]:
                skipped += 1
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
        net = r[7] if r[0] == 'seg' else r[5]
        shape = (pcbnew.SHAPE_SEGMENT(t.GetStart(), t.GetEnd(), t.GetWidth()) if r[0] == 'seg'
                 else pcbnew.SHAPE_CIRCLE(t.GetPosition(), r[3] // 2))
        for f in board.GetFootprints():
            for p in f.Pads():
                if p.GetNetname() != net and p.GetEffectiveShape(pcbnew.F_Cu).Collide(shape, pcbnew.FromMM(0.15)):
                    raise SystemExit('возврат %s задевает %s.%s (%s) — плату не сохраняю'
                                     % (key, f.GetReference(), p.GetNumber(), p.GetNetname()))
        board.Add(t)
        restored += 1
        print('   возвращено:', key)
    total = len({seg_key(t) for t in board.GetTracks()})
    print('элементов меди: закреплено было %d, возвращено %d, отброшено нулевых %d, сейчас %d'
          % (len(snap), restored, skipped, total))
    nets = {t.GetNetname() for t in board.GetTracks() if WANTED(t.GetNetname())}
    print('дочищено висящих после трассировки:', prune(board, nets=nets))
    add_gnd_vias(board)
    for t in board.GetTracks():
        t.SetLocked(False)
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcb_route.save(board, board_path)


NEW_REFS = ('Q10', 'Q11', 'Q12', 'R119', 'R120', 'R121', 'R122', 'U24')


def add_gnd_vias(board):
    """Каждой площадке GND новых деталей — свой переход на плоскость In1 рядом, дорожкой 0,3 мм по F.Cu.
    Место — первое из кругов 1,0–2,6 мм вокруг площадки, где переход и дорожка не ближе 0,2 мм к чужой меди."""
    clr = MM(0.2)
    d, drill = MM(GND_VIA[0]), MM(GND_VIA[1])
    gnd = board.FindNet('GND')
    others = [t for t in board.GetTracks() if t.GetNetname() != 'GND']
    pads = [(f, p) for f in board.GetFootprints() for p in f.Pads()]

    def free(shape, layers, skip_pad):
        for t in others:
            if isinstance(t, pcbnew.PCB_VIA):
                if t.GetEffectiveShape(pcbnew.F_Cu).Collide(shape, clr):
                    return False
            elif t.GetLayer() in layers and t.GetEffectiveShape(t.GetLayer()).Collide(shape, clr):
                return False
        for f, p in pads:
            if p is skip_pad or p.GetNetname() == 'GND':
                continue
            for L in layers:
                if p.IsOnLayer(L) and p.GetEffectiveShape(L).Collide(shape, clr):
                    return False
        return True

    def under_part(v):
        for f in board.GetFootprints():          # не ставить переход под корпус детали
            cy = f.GetCourtyard(pcbnew.F_CrtYd)
            if cy.OutlineCount() and cy.Contains(v):
                return True
        return False

    for f in board.GetFootprints():
        if f.GetReference() not in NEW_REFS:
            continue
        for p in f.Pads():
            if p.GetNetname() != 'GND':
                continue
            c = p.GetPosition()
            done = False
            for r in [x / 10 for x in range(10, 27, 2)]:
                for k in range(16):
                    a = 2 * math.pi * k / 16
                    v = pcbnew.VECTOR2I(c.x + MM(r * math.cos(a)), c.y + MM(r * math.sin(a)))
                    via_sh = pcbnew.SHAPE_CIRCLE(v, d // 2)
                    seg_sh = pcbnew.SHAPE_SEGMENT(c, v, MM(0.3))
                    if under_part(v) or not free(via_sh, [pcbnew.F_Cu, pcbnew.B_Cu], p) or not free(seg_sh, [pcbnew.F_Cu], p):
                        continue
                    via = pcbnew.PCB_VIA(board)
                    via.SetPosition(v)
                    try:
                        via.SetWidth(d)
                    except TypeError:
                        via.SetWidth(pcbnew.F_Cu, d)
                    via.SetDrill(drill)
                    via.SetNet(gnd)
                    board.Add(via)
                    tr = pcbnew.PCB_TRACK(board)
                    tr.SetStart(c)
                    tr.SetEnd(v)
                    tr.SetWidth(MM(0.3))
                    tr.SetLayer(pcbnew.F_Cu)
                    tr.SetNet(gnd)
                    board.Add(tr)
                    print('%s.%s → переход GND (%.2f; %.2f)' % (f.GetReference(), p.GetNumber(),
                                                               pcbnew.ToMM(v.x), pcbnew.ToMM(v.y)))
                    done = True
                    break
                if done:
                    break
            if not done:
                raise SystemExit('нет места для перехода GND у %s.%s' % (f.GetReference(), p.GetNumber()))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'prepare':
        prepare(*sys.argv[2:6])
    elif cmd == 'export':
        export(*sys.argv[2:4])
    elif cmd == 'finish':
        finish(*sys.argv[2:4])
    else:
        raise SystemExit('prepare | export | finish')
