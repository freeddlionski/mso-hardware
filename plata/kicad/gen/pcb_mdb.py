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
    on_board = {f.GetReference(): f for f in board.GetFootprints()}
    for ref, f in list(on_board.items()):
        if ref.startswith(('H', 'TP')) and ref not in comps:
            continue                                   # крепёж добавляет pcb_build сам
        if ref in comps:
            continue
        for p in f.Pads():
            if p.GetNetname():
                dirty.append((p.GetPosition(), p.GetNetname(), p.GetEffectiveShape()))
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
            if v and f.GetFieldText(key) != v:
                f.SetField(key, v)
                fld = f.GetFieldByName(key)
                if fld:
                    fld.SetVisible(False)
        if f.IsDNP() != bool(c.dnp):
            f.SetDNP(bool(c.dnp))
        for p in f.Pads():
            want = c.pins.get(p.GetNumber(), '')
            if want.startswith('unconnected-'):
                want = ''
            have = p.GetNetname()
            if want != have:
                if have:
                    dirty.append((p.GetPosition(), have, p.GetEffectiveShape()))
                if want:
                    p.SetNet(board.FindNet(want))
                else:
                    p.SetNetCode(0)
                print('цепь площадки %s.%s: %s → %s' % (ref, p.GetNumber(), have or '—', want or '—'))

    # --- дорожки: снять цепи, которых нет, и обрывки у изменённых площадок ---
    removed = 0
    for t in list(board.GetTracks()):
        if t.GetNetname() and t.GetNetname() not in nets:
            board.Remove(t)
            removed += 1
    pads = []
    for f in board.GetFootprints():
        for p in f.Pads():
            pads.append({'net': p.GetNetname(), 'shape': p.GetEffectiveShape(), 'pos': p.GetPosition()})

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
            for e in ends:
                sh = pcbnew.SHAPE_CIRCLE(e, MM(0.05))
                queue.append((e, net, sh))
    print('снято дорожек и переходов:', removed)

    # --- закрепить всё оставшееся, снимок для проверки после трассировки ---
    snap = []
    for t in board.GetTracks():
        t.SetLocked(True)
        snap.append(list(seg_key(t)))
    json.dump(snap, open(snapshot, 'w'), ensure_ascii=False)
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcb_route.save(board, board_path)
    print('закреплено элементов меди:', len(snap))


def finish(board_path, snapshot):
    board = pcb_route.load(board_path)
    before = {tuple(tuple(x) if isinstance(x, list) else x for x in s) for s in json.load(open(snapshot))}
    now = {seg_key(t) for t in board.GetTracks()}
    lost = before - now
    print('элементов меди: было закреплено %d, сейчас всего %d, новых %d, пропало %d'
          % (len(before), len(now), len(now - before), len(lost)))
    for k in list(lost)[:20]:
        print('   пропало:', k)
    if lost:
        raise SystemExit('Freerouting сдвинул закреплённую медь — плату не сохраняю')
    for t in board.GetTracks():
        t.SetLocked(False)
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcb_route.save(board, board_path)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'prepare':
        prepare(*sys.argv[2:6])
    elif cmd == 'finish':
        finish(*sys.argv[2:4])
    else:
        raise SystemExit('prepare | finish')
