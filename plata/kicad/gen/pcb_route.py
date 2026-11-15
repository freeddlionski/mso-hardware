"""Трассировка платы в CI (образ kicad/kicad:9.0, нужен pcbnew):

  python3 pcb_route.py prep   <плата.kicad_pcb> <выход.dsn>   — плоскости In1 (GND) и In2 (+24V_P / +3V3), экспорт Specctra
  python3 pcb_route.py finish <плата.kicad_pcb> <вход.ses>    — импорт дорожек Freerouting, заливки GND на F/B, заливка зон

Плата редактируется на месте (тот же файл). Правила и классы цепей — в mso74-plata.kicad_pro (pcb_rules.py).
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcb_rules  # noqa: E402
from pcb_build import ORIGIN, mm  # noqa: E402

W, H = 240.0, 120.0
HOLES = [(4, 4), (236, 4), (4, 116), (236, 116)]


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
        import math
        for i in range(24):
            a = 2 * math.pi * i / 24
            ol.Append(mm(ORIGIN[0] + hx + 3.6 * math.cos(a)), mm(ORIGIN[1] + hy + 3.6 * math.sin(a)))
        board.Add(z)


def prep(path, dsn):
    board = pcbnew.LoadBoard(path)
    full = (0.5, 0.5, W - 0.5, H - 0.5)
    zone(board, 'GND', pcbnew.In1_Cu, full)
    for net, rect in pcb_rules.IN2:
        zone(board, net, pcbnew.In2_Cu, rect)
    keepout_holes(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    ok = pcbnew.ExportSpecctraDSN(board, dsn)
    print('DSN:', dsn, ok)
    if not ok:
        raise SystemExit('экспорт DSN не удался')


def finish(path, ses):
    board = pcbnew.LoadBoard(path)
    try:
        ok = pcbnew.ImportSpecctraSES(board, ses)
    except TypeError:
        ok = pcbnew.ImportSpecctraSES(ses)
    print('SES импортирован:', ok)
    if not ok:
        raise SystemExit('импорт SES не удался')
    full = (0.5, 0.5, W - 0.5, H - 0.5)
    zone(board, 'GND', pcbnew.F_Cu, full, clearance=0.3, thermal=False)
    zone(board, 'GND', pcbnew.B_Cu, full, clearance=0.3, thermal=False)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)
    n = sum(1 for t in board.GetTracks())
    print('дорожек и переходов:', n)


if __name__ == '__main__':
    {'prep': prep, 'finish': finish}[sys.argv[1]](*sys.argv[2:4])
