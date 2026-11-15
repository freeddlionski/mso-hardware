"""Поэтапная трассировка (route.yml, образ kicad/kicad:9.0, нужен pcbnew). Этапы — route_stages.py.

  python3 pcb_route.py init   <плата>                 — плоскости In1 (GND) и In2 (+24V_P / +3V3), запреты у крепежа
  python3 pcb_route.py export <плата> <этап> <dsn>    — Specctra для этапа: вся плата, разводятся цепи этапа и начатые
  python3 pcb_route.py import <плата> <ses>           — дорожки Freerouting в плату (плата правится на месте)
  python3 pcb_route.py view   <плата> <копия>         — копия с заливками GND на F/B — для DRC и картинок

Правила и классы цепей — mso74-plata.kicad_pro (pcb_rules.py).
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcb_rules  # noqa: E402
import route_stages  # noqa: E402
from pcb_build import ORIGIN, mm  # noqa: E402

W, H = 240.0, 120.0
HOLES = [(4, 4), (236, 4), (4, 116), (236, 116)]
FULL = (0.5, 0.5, W - 0.5, H - 0.5)


def pro_of(path):
    return os.path.splitext(path)[0] + '.kicad_pro'


def save(board, path):
    pcbnew.SaveBoard(path, board)
    pcb_rules.apply_to_pro(pro_of(path))     # SaveBoard пишет .kicad_pro по умолчанию — вернуть наши правила


def load(path):
    pcb_rules.apply_to_pro(pro_of(path))
    return pcbnew.LoadBoard(path)


def zone(board, net, layer, rect, prio=0, clearance=0.3, thermal=True):
    x0, y0, x1, y1 = rect
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    ni = board.FindNet(net)
    if ni is None:
        raise SystemExit('нет цепи ' + net)
    z.SetNet(ni)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ol.Append(mm(ORIGIN[0] + x), mm(ORIGIN[1] + y))
    z.SetAssignedPriority(prio)
    z.SetLocalClearance(mm(clearance))
    z.SetMinThickness(mm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL if thermal else pcbnew.ZONE_CONNECTION_FULL)
    z.SetThermalReliefGap(mm(0.3))
    z.SetThermalReliefSpokeWidth(mm(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    board.Add(z)
    return z


def keepout_holes(board):
    """Медь не ближе 3,6 мм к центру крепёжных отверстий (головка/шайба M3)."""
    for hx, hy in HOLES:
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(pcbnew.LSET.AllCuMask())
        ol = z.Outline()
        ol.NewOutline()
        for i in range(24):
            a = 2 * math.pi * i / 24
            ol.Append(mm(ORIGIN[0] + hx + 3.6 * math.cos(a)), mm(ORIGIN[1] + hy + 3.6 * math.sin(a)))
        board.Add(z)


def init(path):
    board = load(path)
    # In1 — сплошная земля: тип «питание» → в Specctra (type power), трассировщик по нему дорожки не ведёт.
    # (Первый прогон без этого проложил по In1 сигналы и даже 24 В — разрезал опорную землю.)
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    zone(board, 'GND', pcbnew.In1_Cu, FULL)
    for net, rect in pcb_rules.IN2:
        zone(board, net, pcbnew.In2_Cu, rect)
    keepout_holes(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    save(board, path)
    print('init: плоскости и запреты добавлены')


def export(path, stage, dsn):
    board = load(path)
    routed = {t.GetNetname() for t in board.GetTracks()}
    hidden, kept = set(), set()
    for f in board.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            if not n:
                continue
            if route_stages.in_stage(n, stage) or n in routed:
                kept.add(n)
            else:
                hidden.add(n)
                p.SetNetCode(0)              # только в памяти: для трассировщика это препятствие без цепи
    print('этап %s: разводятся %d цепей, отложено %d; дорожек на плате %d'
          % (stage, len(kept), len(hidden), len(list(board.GetTracks()))))
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit('экспорт DSN не удался')


def imp(path, ses):
    board = load(path)
    try:
        ok = pcbnew.ImportSpecctraSES(board, ses)
    except TypeError:
        ok = pcbnew.ImportSpecctraSES(ses)
    if not ok:
        raise SystemExit('импорт SES не удался')
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    save(board, path)
    tracks = list(board.GetTracks())
    print('импорт: дорожек и переходов %d, цепей с дорожками %d' % (len(tracks), len({t.GetNetname() for t in tracks})))


def view(path, out):
    board = load(path)
    zone(board, 'GND', pcbnew.F_Cu, FULL, thermal=False)
    zone(board, 'GND', pcbnew.B_Cu, FULL, thermal=False)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    save(board, out)


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    {'init': init, 'export': export, 'import': imp, 'view': view}[cmd](*args)
