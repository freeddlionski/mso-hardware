"""Табло 5 В: Mini-Fit J3/J4 → несъёмные винтовые клеммы 5,08 (Павел 17.11.2026) + подпись HUB75.

python3 pcb_tablo.py BOARD.kicad_pcb  — правит готовую плату на месте (pcbnew, контейнер kicad/kicad:9.0).

Клемма — официальное посадочное место TerminalBlock_Phoenix_MKDS-1,5-2-5.08 (KANGNEX WJ500V-5.08-2P, C8465),
поворот 270°: провод заходит с левой кромки, вывод 1 (+5V) сверху, вывод 2 (GND) на 5,08 ниже. Вывод 1 сдвинут влево
до 34,4 (корпус не налезает на C34); к старой точке вывода 1 — короткая дорожка 3 мм той же цепи. GND — через
плоскость In1. После замены все зоны перезаливаются; проверка — DRC в kicad.yml.
"""
import os
import sys
import pcbnew
import pcb_route

MM = pcbnew.FromMM
LIB = 'TerminalBlock_Phoenix'
NAME = 'TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'
X_PAD = 34.4
# ref: (y вывода 1, подпись, y строк подписи)
TERMS = {'J3': (56.0, 'ТАБЛО 1', (49.4, 51.4)), 'J4': (86.0, 'ТАБЛО 2', (79.4, 81.4))}


def libdir():
    for d in (os.environ.get('KICAD9_FOOTPRINT_DIR', ''), '/usr/share/kicad/footprints'):
        p = os.path.join(d, LIB + '.pretty')
        if d and os.path.isdir(p):
            return p
    raise SystemExit('нет библиотеки ' + LIB)


def text(board, s, x, y, h):
    t = pcbnew.PCB_TEXT(board)
    t.SetLayer(pcbnew.F_SilkS)
    t.SetText(s)
    t.SetTextSize(pcbnew.VECTOR2I(MM(h), MM(h)))
    t.SetTextThickness(MM(0.15))
    t.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    board.Add(t)


def main(path):
    board = pcb_route.load(path)
    lib = libdir()
    for ref, (y1, title, (ya, yb)) in TERMS.items():
        old = board.FindFootprintByReference(ref)
        if old.GetFPID().GetLibItemName().wx_str() == NAME:
            print(ref, 'уже клемма')
            continue
        old_pad1 = [p for p in old.Pads() if p.GetNumber() == '1'][0]
        p1 = old_pad1.GetPosition()
        nets = {p.GetNumber(): p.GetNetname() for p in old.Pads()}
        new = pcbnew.FootprintLoad(lib, NAME)
        new.SetFPID(pcbnew.LIB_ID(LIB, NAME))
        new.SetParent(board)
        new.SetReference(ref)
        new.SetValue(old.GetValue())
        for f in old.GetFields():
            n = f.GetName()
            if n in ('Reference', 'Value', 'Footprint', 'Datasheet', 'Description'):
                continue
            nf = pcbnew.PCB_FIELD(new, new.GetNextFieldId(), n)
            nf.SetText(f.GetText())
            nf.SetVisible(False)
            nf.SetLayer(pcbnew.F_Fab)
            new.AddField(nf)
        new.SetPath(old.GetPath())
        new.SetSheetname(old.GetSheetname())
        new.SetSheetfile(old.GetSheetfile())
        new.SetOrientationDegrees(270)
        new.SetPosition(pcbnew.VECTOR2I(MM(X_PAD), MM(y1)))
        new.Reference().SetVisible(False)          # номер — в Fab и координатах; на шелке подпись «ТАБЛО N»
        board.Remove(old)
        board.Add(new)
        for p in new.Pads():
            p.SetNet(board.FindNet(nets[p.GetNumber()]))
        # дорожка от старой точки вывода 1 к новой (та же ширина, что у подходящей)
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(p1)
        tr.SetEnd(pcbnew.VECTOR2I(MM(X_PAD), MM(y1)))
        tr.SetWidth(MM(3.0))
        tr.SetLayer(pcbnew.F_Cu)
        tr.SetNet(board.FindNet(nets['1']))
        board.Add(tr)
        text(board, title, 35.6, ya, 1.2)
        text(board, "+5V сверху", 35.6, yb, 1.0)
        print(ref, '→ клемма', NAME, 'вывод 1 (%.2f; %.2f)' % (X_PAD, y1))
    # HUB75 — справа от шлейфа J14 у верхней кромки
    if not any(isinstance(d, pcbnew.PCB_TEXT) and d.GetText() == 'HUB75' for d in board.Drawings()):
        text(board, 'HUB75', 155.5, 35.5, 1.5)
    board.BuildConnectivity()
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcb_route.save(board, path)


if __name__ == '__main__':
    main(sys.argv[1])

