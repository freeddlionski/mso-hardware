"""Полоса подписей под клеммами: плата 240 × 120 → 240 × 127 (вровень с табло; Павел 16.11.2026).

python3 pcb_strip.py BOARD.kicad_pcb  — правит файл на месте (S-expression, без pcbnew).

Нижний край опускается на 7 мм; нижние отверстия H3/H4 и их запретные зоны — вместе с ним.
Ручные подписи над клеммами снимаются (кроме шильдика), в новой полосе под каждой клеммой:
строка выводов ровно под выводами и строка назначения под ней. Медь, детали и дорожки не меняются.
"""
import sys
import uuid
from pathlib import Path
from sexp import parse, find, findall, dump, Q

OLD, NEW = 150.0, 157.0          # нижний край, мм (координаты файла)
DY = NEW - OLD
PIN_Y, TITLE_Y = 151.6, 154.3    # центры строк: выводы (корпус клеммы кончается на 150,5) и назначение
PIN_H, TITLE_H = 0.9, 1.2

# Клемма → (назначение, подписи выводов по номерам 1, 2, …)
STRIP = {
    'J1': ('ПИТАНИЕ 24V', ['+24V', 'GND']),
    'J2': ('VTK 24V', ['+24V', 'GND']),
    'J9': ('VTK RS-232', ['TXD', 'RXD', 'GND']),
    'J8': ('RS-485', ['A', 'B', 'GND']),
    'J11': ('МОНЕТНИК', ['+12', 'GND', 'ИМП', 'БЛК']),
    'J12': ('КУПЮРНИК', ['+24', '+12', 'GND', 'ИМП']),
    'J10': ('MDB', []),
    'J13': ('СЕРВИС', ['КН', 'GND']),
    'J15': ('ВХОДЫ', ['1', '2', '3', '4', 'GND', 'GND']),
    'J16': ('ВЫХОДЫ 24V', ['+24', '1', '2', '3', '4', 'GND']),
}


def num(v):
    return ('%.6f' % v).rstrip('0').rstrip('.')


def text(s, x, y, h):
    return ['gr_text', Q(s), ['at', num(x), num(y), '0'], ['layer', Q('F.SilkS')], ['uuid', Q(str(uuid.uuid4()))],
            ['effects', ['font', ['size', num(h), num(h)], ['thickness', '0.15']]]]


def shift_pts(node):
    for p in find(find(node, 'polygon'), 'pts')[1:]:
        if float(p[2]) >= OLD - 10:
            p[2] = num(float(p[2]) + DY)


def main(path):
    tree = parse(Path(path).read_text(encoding='utf-8'))
    # край платы
    for g in tree:
        if isinstance(g, list) and g and g[0] == 'gr_line' and find(g, 'layer')[1] == 'Edge.Cuts':
            for k in ('start', 'end'):
                e = find(g, k)
                if float(e[2]) == OLD:
                    e[2] = num(NEW)
    # нижние отверстия и их запретные зоны, защитная полоса правого края
    for fp in findall(tree, 'footprint'):
        ref = {p[1]: p[2] for p in findall(fp, 'property')}['Reference']
        at = find(fp, 'at')
        if ref in ('H3', 'H4') and float(at[2]) == OLD - 4:
            at[2] = num(float(at[2]) + DY)
    for z in findall(tree, 'zone'):
        if find(z, 'net_name')[1] == '':
            ys = [float(p[2]) for p in find(find(z, 'polygon'), 'pts')[1:]]
            if max(ys) >= OLD - 1:
                if min(ys) > OLD - 10:            # круг у H3/H4 — целиком вниз
                    for p in find(find(z, 'polygon'), 'pts')[1:]:
                        p[2] = num(float(p[2]) + DY)
                else:                             # полоса вдоль правого края — удлинить
                    for p in find(find(z, 'polygon'), 'pts')[1:]:
                        if float(p[2]) == OLD:
                            p[2] = num(NEW)
    # ручные подписи над клеммами — убрать (шильдик оставить)
    tree[:] = [g for g in tree if not (isinstance(g, list) and g and g[0] == 'gr_text'
                                      and find(g, 'layer')[1] == 'F.SilkS' and not g[1].startswith('MCO74'))]
    # полоса подписей
    fps = {{p[1]: p[2] for p in findall(fp, 'property')}['Reference']: fp for fp in findall(tree, 'footprint')}
    for ref, (title, pins) in STRIP.items():
        fp = fps[ref]
        ax, ay = float(find(fp, 'at')[1]), float(find(fp, 'at')[2])
        px = {p[1]: ax + float(find(p, 'at')[1]) for p in findall(fp, 'pad')}
        for i, s in enumerate(pins, 1):
            tree.append(text(s, px[str(i)], PIN_Y, PIN_H))
        xs = [px[k] for k in px if k.isdigit()]
        tree.append(text(title, (min(xs) + max(xs)) / 2, TITLE_Y, TITLE_H))
    Path(path).write_text(dump(tree) + '\n', encoding='utf-8')
    print('плата 240 ×', int(NEW - 30), 'мм; подписей в полосе:', sum(len(p) + 1 for _, p in STRIP.values()))


if __name__ == '__main__':
    main(sys.argv[1])
