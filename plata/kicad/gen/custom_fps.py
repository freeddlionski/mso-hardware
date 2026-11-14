"""Свои посадочные места (библиотека mso74.pretty) — только то, чего нет в официальной библиотеке KiCad.

Texas_RJR_VQFN-HR-14_3.5x4mm — LM61460 (TI RJR0014A, VQFN-HR-14, корпус 4 × 3,5 мм).
Площадки взяты из проекта github.com/jessiepullaro414/Fascia (MIT, коммит 62bdc7e): там они извлечены из векторного
чертежа LAND PATTERN EXAMPLE в TI SNVSB70F. Сверено 2026-11-14 с размерами чертежа TI 4223976 (RJR0014A):
6 площадок 0,7 × 0,25 (выв. 2, 4, 6, 7, 13, 14); выв. 3 — 0,7 × 0,3; выв. 8 и 12 (VIN) — 1,0 × 0,4; выв. 10 (SW) — 2,4 × 0,4;
угловые 1, 5, 9, 11 — Г-образные, по высоте 1,0 × 0,4, полки 0,45 × 0,7 (слева) и 0,45 × 0,8 (справа);
центры: ряд слева x = −1,85; ряды сверху/снизу y = ±1,6 (расстояние 3,2); VIN y = ±1,45 (2,9); шаг 0,5 / 0,525 / 0,625.
Нумерация совпадает с символом mso74:LM61460 (VIN рядом с PGND по обе стороны — как в TI «Pin Functions»).
Маска NSMD +0,05 мм (TI: не более 0,07); паста угловых 1/5/9/11 — 90 % площади (TI, Solder Paste Example).
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
        # TI 4223976: маска NSMD, окно не более 0,07 мм с каждой стороны → 0,05;
        # паста: угловые 1/5/9/11 — 90 % площади (−5 % по каждой стороне), остальные — 100 %
        paste = ' (solder_paste_margin_ratio -0.05)' if num in ('1', '5', '9', '11') else ''
        lines.append('  (pad "%s" smd rect (at %s %s) (size %s %s) (layers "F.Cu" "F.Paste" "F.Mask")'
                     ' (solder_mask_margin 0.05)%s)' % (num, _fmt(x), _fmt(y), _fmt(w), _fmt(h), paste))
    lines.append(')')
    return '\n'.join(lines) + '\n'


# CSD19534Q5A, TI VSONP-8 (DQJ, «Q5A»), 5 × 6 мм. Геометрия — из KiCad 9 Package_SON:VSONP-8-1EP_5x6_P1.27mm
# (сделан по TI CSD18531Q5A, тот же корпус Q5A), но нумерация там 1 = S, 2 = G, 3 = D, а у символа
# Transistor_FET:CSD19534Q5A — 1–3 = S, 4 = G, 5 = D (как в TI). Здесь нумерация как у символа и TI.
# Сверено с TI SLPS483 §7.2 «Recommended PCB Pattern» (таблица F1–F11): общий размер 6,3 (F1 6,205–6,305),
# площадки выводов 0,7 × 0,7 (F4 0,65–0,7; F7 0,7–0,8), высота ряда и стока 4,51 (F2/F3/F11 4,46–4,56),
# длина сток + площадки 4,995 (F10 4,9–5,0). Привязку остальных F к рисунку — сверить глазами по PDF TI.
DQJ_PADS = [
    ('1', -2.8, -1.905, 0.7, 0.7), ('2', -2.8, -0.635, 0.7, 0.7), ('3', -2.8, 0.635, 0.7, 0.7),
    ('4', -2.8, 1.905, 0.7, 0.7),
    ('5', 2.8, -1.905, 0.7, 0.7), ('5', 2.8, -0.635, 0.7, 0.7), ('5', 2.8, 0.635, 0.7, 0.7), ('5', 2.8, 1.905, 0.7, 0.7),
]
DQJ_EP = (0.33, 0, 4.35, 4.51)             # сток, без пасты: паста окнами ниже (как в KiCad / TI stencil)
DQJ_PASTE = [(-0.7975, -1.095, 1.235, 1.57), (-0.7975, 1.095, 1.235, 1.57),
             (1.1125, -1.095, 1.585, 1.57), (1.1125, 1.095, 1.585, 1.57)]


def dqj(name):
    lines = [
        '(footprint "%s"' % name, '  (version 20241229)', '  (generator "mso74-gen")', '  (generator_version "9.0")',
        '  (layer "F.Cu")',
        '  (descr "TI VSONP-8 DQJ (Q5A) 5x6mm, CSD19534Q5A; pins 1-3 S, 4 G, 5 D (as TI and KiCad symbol). '
        'Geometry from KiCad Package_SON:VSONP-8-1EP_5x6_P1.27mm, checked vs TI SLPS483 7.2")',
        '  (tags "VSONP DQJ Q5A CSD19534Q5A")',
        '  (property "Reference" "REF**" (at 0 -3.6 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))',
        '  (property "Value" "%s" (at 0 3.6 0) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))' % name,
        '  (attr smd)',
        '  (fp_poly (pts (xy -1.5 -2.5) (xy 3 -2.5) (xy 3 2.5) (xy -3 2.5) (xy -3 -1.5)) '
        '(stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))',
        '  (fp_rect (start -3.45 -2.85) (end 3.45 2.85) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))',
        '  (fp_line (start -1.5 -2.61) (end 3.11 -2.61) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
        '  (fp_line (start -3.11 2.61) (end 3.11 2.61) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))',
        '  (fp_circle (center -3.45 -2.6) (end -3.3 -2.6) (stroke (width 0.12) (type solid)) (fill yes) (layer "F.SilkS"))',
    ]
    for num, x, y, w, h in DQJ_PADS:
        lines.append('  (pad "%s" smd rect (at %s %s) (size %s %s) (layers "F.Cu" "F.Paste" "F.Mask"))'
                     % (num, _fmt(x), _fmt(y), _fmt(w), _fmt(h)))
    x, y, w, h = DQJ_EP
    lines.append('  (pad "5" smd rect (at %s %s) (size %s %s) (layers "F.Cu" "F.Mask"))' % (_fmt(x), _fmt(y), _fmt(w), _fmt(h)))
    for x, y, w, h in DQJ_PASTE:
        lines.append('  (pad "" smd rect (at %s %s) (size %s %s) (layers "F.Paste"))' % (_fmt(x), _fmt(y), _fmt(w), _fmt(h)))
    lines.append(')')
    return '\n'.join(lines) + '\n'


FOOTPRINTS = {
    'Texas_RJR_VQFN-HR-14_3.5x4mm': rjr0014a,
    'Texas_DQJ_VSONP-8_5x6mm_CSD19534Q5A': dqj,
}

# Клеммы KANGNEX: посадочные места Phoenix из KiCad 9 с отверстием по даташиту KANGNEX.
# WJ15EDGRC-3.81: штырь 0,8 × 0,8 (диагональ 1,13), отверстие Ø1,4 (у Phoenix MC в KiCad — 1,2).
# WJ2EDGRC-5.08: штырь 1,0 × 1,0 (диагональ 1,41), отверстие Ø1,7 (по WJ2EDGRTM-5.08 той же серии; в KiCad MSTBA — 1,4,
# меньше диагонали штыря — не встанет). Корпус и шаг — как у Phoenix; положение кромки корпуса сверить по образцу.
DERIVED = {}
for _n in (2, 3, 4, 5, 6):
    DERIVED['KANGNEX_WJ15EDGRC_1x%02d_P3.81mm_Drill1.4' % _n] = (
        'Connector_Phoenix_MC.pretty/PhoenixContact_MC_1,5_%d-G-3.81_1x%02d_P3.81mm_Horizontal' % (_n, _n), '1.2', '1.4')
DERIVED['KANGNEX_WJ2EDGRC_1x02_P5.08mm_Drill1.7'] = (
    'Connector_Phoenix_MSTB.pretty/PhoenixContact_MSTBA_2,5_2-G-5,08_1x02_P5.08mm_Horizontal', '1.4', '1.7')


def derive(fpdir, name, src, old_drill, new_drill):
    text = open(os.path.join(fpdir, src + '.kicad_mod'), encoding='utf-8').read()
    old_name = src.split('/')[-1]
    n = text.count('(drill %s)' % old_drill)
    assert n >= 2 and '(drill' not in text.replace('(drill %s)' % old_drill, ''), (src, n)
    text = text.replace('(drill %s)' % old_drill, '(drill %s)' % new_drill).replace(old_name, name)
    text = text.replace('(descr "', '(descr "KANGNEX: drill %s mm per KANGNEX datasheet; based on KiCad ' % new_drill, 1)
    return text


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


def write(libdir, fpdir):
    """fpdir — каталог footprints из ветки kicad-libs (официальные посадочные места KiCad 9)."""
    check()
    pretty = os.path.join(libdir, 'mso74.pretty')
    os.makedirs(pretty, exist_ok=True)
    for name, fn in FOOTPRINTS.items():
        with open(os.path.join(pretty, name + '.kicad_mod'), 'w', encoding='utf-8') as f:
            f.write(fn(name))
    for name, (src, old, new) in DERIVED.items():
        with open(os.path.join(pretty, name + '.kicad_mod'), 'w', encoding='utf-8') as f:
            f.write(derive(fpdir, name, src, old, new))
    return set(FOOTPRINTS) | set(DERIVED)
