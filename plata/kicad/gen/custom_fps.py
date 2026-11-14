"""Свои посадочные места (библиотека mso74.pretty) — только то, чего нет в официальной библиотеке KiCad.

Texas_RJR_VQFN-HR-14_3.5x4mm — LM61460 (TI RJR0014A, VQFN-HR-14, корпус 4 × 3,5 мм).
Площадки взяты из проекта github.com/jessiepullaro414/Fascia (MIT, коммит 62bdc7e): там они извлечены из векторного
чертежа LAND PATTERN EXAMPLE в TI SNVSB70F. Сверено 2026-11-14 с размерами чертежа TI 4223976 (RJR0014A):
6 площадок 0,7 × 0,25 (выв. 2, 4, 6, 7, 13, 14); выв. 3 — 0,7 × 0,3; выв. 8 и 12 (VIN) — 1,0 × 0,4; выв. 10 (SW) — 2,4 × 0,4;
угловые 1, 5, 9, 11 — Г-образные, по высоте 1,0 × 0,4, полки 0,45 × 0,7 (слева) и 0,45 × 0,8 (справа);
центры: ряд слева x = −1,85; ряды сверху/снизу y = ±1,6 (расстояние 3,2); VIN y = ±1,45 (2,9); шаг 0,5 / 0,525 / 0,625.
Нумерация совпадает с символом mso74:LM61460 (VIN рядом с PGND по обе стороны — как в TI «Pin Functions»).
Перед заказом плат — сверить с PDF TI ещё раз глазами (наложить чертёж).
"""
import os

# (номер, x, y, ширина, высота) — мм, вид сверху, вывод 1 слева вверху
RJR_PADS = [
    ('1', -1.700, -1.675, 0.400, 0.550), ('1', -1.850, -1.175, 0.700, 0.450),
    ('2', -1.850, -0.525, 0.700, 0.250),
    ('3', -1.850, 0.000, 0.700, 0.300),
    ('4', -1.850, 0.525, 0.700, 0.250),
    ('5', -1.850, 1.175, 0.700, 0.450), ('5', -1.700, 1.675, 0.400, 0.550),
    ('6', -1.125, 1.600, 0.250, 0.700),
    ('7', -0.625, 1.600, 0.250, 0.700),
    ('8', 0.450, 1.450, 0.400, 1.000),
    ('9', 1.800, 1.175, 0.800, 0.450), ('9', 1.600, 1.675, 0.400, 0.550),
    ('10', 1.000, 0.000, 2.400, 0.400),
    ('11', 1.600, -1.675, 0.400, 0.550), ('11', 1.800, -1.175, 0.800, 0.450),
    ('12', 0.450, -1.450, 0.400, 1.000),
    ('13', -0.625, -1.600, 0.250, 0.700),
    ('14', -1.125, -1.600, 0.250, 0.700),
]


def _fmt(v):
    return ('%.3f' % v).rstrip('0').rstrip('.')


def rjr0014a(name):
    lines = [
        '(footprint "%s"' % name,
        '  (version 20241229)',
        '  (generator "mso74-gen")',
        '  (generator_version "9.0")',
        '  (layer "F.Cu")',
        '  (descr "TI RJR0014A VQFN-HR-14 4x3.5mm (LM61460). Pads per TI SNVSB70F land pattern; L-shaped pads 1/5/9/11 '
        'are two rectangles with one number. https://www.ti.com/lit/ds/symlink/lm61460.pdf")',
        '  (tags "VQFN-HR RJR0014A LM61460 TI")',
        '  (property "Reference" "REF**" (at 0 -2.9 0) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
        '  (property "Value" "%s" (at 0 2.9 0) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))' % name,
        '  (attr smd)',
        # корпус 4 × 3,5 со скосом у вывода 1
        '  (fp_poly (pts (xy -1.5 -1.75) (xy 2 -1.75) (xy 2 1.75) (xy -2 1.75) (xy -2 -1.25)) '
        '(stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))',
        '  (fp_rect (start -2.45 -2.2) (end 2.45 2.2) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))',
        # шелкография: только метка вывода 1 (вокруг корпуса места нет — площадки у края)
        '  (fp_circle (center -2.55 -2.05) (end -2.4 -2.05) (stroke (width 0.12) (type solid)) (fill yes) (layer "F.SilkS"))',
        '  (fp_text user "${REFERENCE}" (at 0.4 0.9 0) (layer "F.Fab") (effects (font (size 0.5 0.5) (thickness 0.08))))',
    ]
    for num, x, y, w, h in RJR_PADS:
        lines.append('  (pad "%s" smd rect (at %s %s) (size %s %s) (layers "F.Cu" "F.Paste" "F.Mask"))'
                     % (num, _fmt(x), _fmt(y), _fmt(w), _fmt(h)))
    lines.append(')')
    return '\n'.join(lines) + '\n'


FOOTPRINTS = {
    'Texas_RJR_VQFN-HR-14_3.5x4mm': rjr0014a,
}


def check():
    """Самопроверка таблицы: 14 выводов, разные выводы не ближе 0,15 мм, всё внутри курта, SW 2,4 × 0,4."""
    nums = {p[0] for p in RJR_PADS}
    assert nums == {str(i) for i in range(1, 15)}, nums
    rects = [(n, x - w / 2, y - h / 2, x + w / 2, y + h / 2) for n, x, y, w, h in RJR_PADS]
    for i, a in enumerate(rects):
        assert -2.45 < a[1] and a[3] < 2.45 and -2.2 < a[2] and a[4] < 2.2, a
        for b in rects[i + 1:]:
            if a[0] != b[0]:
                gap_x = max(b[1] - a[3], a[1] - b[3])
                gap_y = max(b[2] - a[4], a[2] - b[4])
                assert max(gap_x, gap_y) >= 0.15 - 1e-9, (a, b, gap_x, gap_y)
    p10 = [p for p in RJR_PADS if p[0] == '10'][0]
    assert (p10[3], p10[4]) == (2.4, 0.4)


def write(libdir):
    check()
    pretty = os.path.join(libdir, 'mso74.pretty')
    os.makedirs(pretty, exist_ok=True)
    for name, fn in FOOTPRINTS.items():
        with open(os.path.join(pretty, name + '.kicad_mod'), 'w', encoding='utf-8') as f:
            f.write(fn(name))
    return set(FOOTPRINTS)
