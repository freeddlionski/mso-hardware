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
import json
import math
import sys

import pcbnew

import netlist
import pcb_build
import pcb_route

MM = pcbnew.FromMM


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


def prepare(board_path, net_path, placement, snapshot):
    board = pcb_route.load(board_path)
    comps, nets = netlist.read(net_path)
    pl = json.load(open(placement, encoding='utf-8'))

    # --- цепи: новые имена ---
    for name in sorted(nets):
        if name and not name.startswith('unconnected-') and not board.FindNet(name):
            ni = pcbnew.NETINFO_ITEM(board, name)
            board.Add(ni)
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
                dirty.append((p.GetPosition(), p.GetNetname(), p.GetEffectiveShape(pcbnew.F_Cu)))
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
                    dirty.append((p.GetPosition(), have, p.GetEffectiveShape(pcbnew.F_Cu)))
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
                        dirty.append((e, net, pcbnew.SHAPE_CIRCLE(e, MM(0.05))))
    for t in list(board.GetTracks()):
        if t.GetNetname() and t.GetNetname() not in nets:
            board.Remove(t)
            removed += 1
    pads = []
    for f in board.GetFootprints():
        for p in f.Pads():
            pads.append({'net': p.GetNetname(), 'shape': p.GetEffectiveShape(pcbnew.F_Cu), 'pos': p.GetPosition()})

    def anchored(pos, net, tr):
        """Точка держится: площадка той же цепи, другой элемент меди той же цепи (кроме tr) или заливка."""
        for p in pads:
            if p['net'] == net and p['shape'].Collide(pos, 0):
                return True
        layers = [tr.GetLayer()] if not isinstance(tr, pcbnew.PCB_VIA) else list(tr.GetLayerSet().CuStack())
        for z in board.Zones():
            if z.GetIsRuleArea() or z.GetNetname() != net:
                continue
            for L in layers:
                if z.IsOnLayer(L) and z.HitTestFilledArea(L, pos):
                    return True
        for o in board.GetTracks():
            if o is tr or o.GetNetname() != net:
                continue
            if not isinstance(o, pcbnew.PCB_VIA) and o.GetStart() == o.GetEnd():
                continue                                   # отрезок нулевой длины — не опора
            if isinstance(o, pcbnew.PCB_VIA):
                if (o.GetPosition() - pos).EuclideanNorm() <= o.GetWidth(pcbnew.F_Cu) // 2:
                    return True
            else:
                if isinstance(tr, pcbnew.PCB_VIA) or o.GetLayer() == tr.GetLayer():
                    if o.GetStart() == pos or o.GetEnd() == pos or o.HitTest(pos, 0):
                        return True
        return False

    def touches(t, point, shape):
        if isinstance(t, pcbnew.PCB_VIA):
            return shape.Collide(t.GetPosition(), t.GetWidth(pcbnew.F_Cu) // 2)
        return shape.Collide(t.GetStart(), 0) or shape.Collide(t.GetEnd(), 0)

    queue = list(dirty)
    while queue:
        point, net, shape = queue.pop()
        for t in list(board.GetTracks()):
            if t.GetNetname() != net or not touches(t, point, shape):
                continue
            ends = [t.GetPosition()] if isinstance(t, pcbnew.PCB_VIA) else [t.GetStart(), t.GetEnd()]
            # снимаем, если хотя бы один конец ни на чём не держится (висит)
            hanging = [e for e in ends if not anchored(e, net, t)]
            if isinstance(t, pcbnew.PCB_VIA):
                n = sum(1 for o in board.GetTracks() if not isinstance(o, pcbnew.PCB_VIA) and o.GetNetname() == net
                        and (o.GetStart() == t.GetPosition() or o.GetEnd() == t.GetPosition()))
                plane = net in ('GND', '+3V3', '+24V_P')
                if not (n == 0 or (n == 1 and not plane)):
                    continue
            elif not hanging:
                continue
            board.Remove(t)
            removed += 1
            for o in list(board.GetTracks()):
                if (not isinstance(o, pcbnew.PCB_VIA) and o.GetNetname() == net and o.GetStart() == o.GetEnd()
                        and any(o.GetStart() == e for e in ends)):
                    board.Remove(o)
                    removed += 1
            for e in ends:
                sh = pcbnew.SHAPE_CIRCLE(e, MM(0.05))
                queue.append((e, net, sh))
    print('снято дорожек и переходов:', removed)

    # --- закрепить всё оставшееся, снимок для проверки после трассировки ---
    snap = []
    for t in board.GetTracks():
        t.SetLocked(True)
        snap.append({'key': list(seg_key(t)), 'raw': seg_raw(t)})
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
    for t in board.GetTracks():
        t.SetLocked(False)
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcb_route.save(board, board_path)


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
