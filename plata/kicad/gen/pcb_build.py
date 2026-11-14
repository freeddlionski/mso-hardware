"""Сборка платы .kicad_pcb из нетлиста и placement.json — выполняется в CI внутри образа kicad/kicad:9.0 (нужен pcbnew).

python3 pcb_build.py <mso74-plata.net> <placement.json> <выход .kicad_pcb>
Плата без дорожек: детали на местах, цепи назначены площадкам (видны «резинки»), контур, 4 отверстия M3,
4 слоя меди. Раскладка правится в pcb_place.py, не в плате.
"""
import json
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import netlist  # noqa: E402

SYS_FP = '/usr/share/kicad/footprints'
OWN_FP = os.path.join(os.path.dirname(HERE), 'lib', 'mso74.pretty')
ORIGIN = (30.0, 30.0)          # левый верхний угол платы на листе, мм


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(ORIGIN[0] + x), mm(ORIGIN[1] + y))


def load(fp):
    lib, name = fp.split(':', 1)
    path = OWN_FP if lib == 'mso74' else os.path.join(SYS_FP, lib + '.pretty')
    f = pcbnew.FootprintLoad(path, name)
    if f is None:
        raise SystemExit('нет посадочного места ' + fp)
    return f


def main(netpath, placement, out):
    comps, nets = netlist.read(netpath)
    pl = json.load(open(placement, encoding='utf-8'))
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(mm(1.6))

    netitems = {}
    for name in sorted(nets):
        if not name or name.startswith('unconnected-'):
            continue
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netitems[name] = ni

    missing = [r for r in comps if r not in pl['parts']]
    if missing:
        raise SystemExit('нет в placement.json: ' + ' '.join(sorted(missing)))
    for ref, c in comps.items():
        x, y, rot = pl['parts'][ref]
        f = load(c.fp)
        f.SetReference(ref)
        f.SetValue(c.value)
        f.SetPosition(pt(x, y))
        f.SetOrientationDegrees(rot)
        try:
            f.SetPath(pcbnew.KIID_PATH(c.path))
        except Exception:
            pass
        for key in ('LCSC', 'MPN'):
            if c.props.get(key):
                try:
                    f.SetField(key, c.props[key])
                except Exception:
                    pass
        if c.dnp:
            try:
                f.SetDNP(True)
            except Exception:
                pass
        for pad in f.Pads():
            n = c.pins.get(pad.GetNumber())
            if n in netitems:
                pad.SetNet(netitems[n])
        f.Reference().SetVisible(True)
        board.Add(f)

    # контур
    w, h = pl['board']['w'], pl['board']['h']
    corners = [(0, 0), (w, 0), (w, h), (0, h)]
    for i in range(4):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(*corners[i]))
        s.SetEnd(pt(*corners[(i + 1) % 4]))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)
    # отверстия M3
    for i, (hx, hy) in enumerate(pl['board']['holes']):
        f = pcbnew.FootprintLoad(os.path.join(SYS_FP, 'MountingHole.pretty'), 'MountingHole_3.2mm_M3')
        f.SetReference('H%d' % (i + 1))
        f.SetPosition(pt(hx, hy))
        board.Add(f)

    pcbnew.SaveBoard(out, board)
    print('плата:', out, 'деталей', len(comps), 'цепей', len(netitems))


if __name__ == '__main__':
    main(*sys.argv[1:4])
