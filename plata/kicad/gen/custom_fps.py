"""Свои посадочные места (библиотека mso74.pretty) — только то, чего нет в официальной библиотеке KiCad.

Texas_RJR_VQFN-HR-14_3.5x4mm — LM61460 (TI RJR0014A, VQFN-HR-14, корпус 4 × 3,5 мм).
Сначала площадки были взяты из проекта Fascia (MIT); 14.11 по векторам PDF TI найдено расхождение 0,05 мм у угловых
1/5/9/11 (нога 1/5 — 0,35, а не 0,4; полки 0,4, а не 0,45) — теперь всё снято с самого чертежа TI.
Нумерация совпадает с символом mso74:LM61460 (TI Table 6-1, Figure 6-1).
Координаты сверены с векторами PDF TI 4223976/H (14.11): см. RJR_CU / RJR_PASTE ниже.
"""
import os

# (номер, x, y, ширина, высота) — мм, вид сверху, вывод 1 слева вверху.
# 2026-11-14: координаты сняты с векторов PDF TI SNVSBD5D, чертёж 4223976/H, стр. 56 (медь) и 57 (паста), масштаб 25X
# откалиброван по площадке 10 (0,4 мм). Г-образные 1/5/9/11 — два прямоугольника с одним номером (перекрываются).
# Скругления TI (R0,05; внутренние R0,12 / паста R0,17) не повторяем — прямые углы.
RJR_CU = [
    ('1', -1.675, -1.450, 0.350, 1.000), ('1', -1.850, -1.150, 0.700, 0.400),
    ('2', -1.850, -0.525, 0.700, 0.250),
    ('3', -1.850, 0.000, 0.700, 0.300),
    ('4', -1.850, 0.525, 0.700, 0.250),
    ('5', -1.675, 1.450, 0.350, 1.000), ('5', -1.850, 1.150, 0.700, 0.400),
    ('6', -1.125, 1.600, 0.250, 0.700),
    ('7', -0.625, 1.600, 0.250, 0.700),
    ('8', 0.450, 1.450, 0.400, 1.000),
    ('9', 1.600, 1.450, 0.400, 1.000), ('9', 1.800, 1.150, 0.800, 0.400),
    ('10', 1.000, 0.000, 2.400, 0.400),
    ('11', 1.600, -1.450, 0.400, 1.000), ('11', 1.800, -1.150, 0.800, 0.400),
    ('12', 0.450, -1.450, 0.400, 1.000),
    ('13', -0.625, -1.600, 0.250, 0.700),
    ('14', -1.125, -1.600, 0.250, 0.700),
]
# паста (TI стр. 57): у 1/5/9/11 нога уже (0,3 / 0,35), полка 0,35 — «90 % по площади»; площадка 10 — два окна 1,1 мм
_PASTE_DIFF = {
    '1': [(-1.650, -1.450, 0.300, 1.000), (-1.850, -1.125, 0.700, 0.350)],
    '5': [(-1.650, 1.450, 0.300, 1.000), (-1.850, 1.125, 0.700, 0.350)],
    '9': [(1.575, 1.450, 0.350, 1.000), (1.800, 1.125, 0.800, 0.350)],
    '11': [(1.575, -1.450, 0.350, 1.000), (1.800, -1.125, 0.800, 0.350)],
    '10': [(0.350, 0.000, 1.100, 0.400), (1.650, 0.000, 1.100, 0.400)],
}
RJR_PASTE = []
_seen = set()
for _n, _x, _y, _w, _h in RJR_CU:
    if _n in _PASTE_DIFF:
        if _n not in _seen:
            RJR_PASTE += [(_n,) + r for r in _PASTE_DIFF[_n]]
    else:
        RJR_PASTE.append((_n, _x, _y, _w, _h))
    _seen.add(_n)
RJR_PADS = RJR_CU   # для check()


def _fmt(v):
    return ('%.3f' % v).rstrip('0').rstrip('.')


def rjr0014a(name):
    lines = [
        '(footprint "%s"' % name,
        '  (version 20241229)',
        '  (generator "mso74-gen")',
        '  (generator_version "9.0")',
        '  (layer "F.Cu")',
        '  (descr "TI RJR0014A VQFN-HR-14 4x3.5mm (LM61460). Pads from TI 4223976/H vectors (SNVSBD5D p.56-57); L-shaped pads 1/5/9/11 '
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
    for num, x, y, w, h in RJR_CU:
        # маска NSMD: окно +0,05 мм (TI: не более 0,07); паста — отдельными окнами по TI
        lines.append('  (pad "%s" smd rect (at %s %s) (size %s %s) (layers "F.Cu" "F.Mask") (solder_mask_margin 0.05))'
                     % (num, _fmt(x), _fmt(y), _fmt(w), _fmt(h)))
    for num, x, y, w, h in RJR_PASTE:
        lines.append('  (pad "" smd rect (at %s %s) (size %s %s) (layers "F.Paste"))' % (_fmt(x), _fmt(y), _fmt(w), _fmt(h)))
    lines.append(')')
    return '\n'.join(lines) + '\n'


# CSD19534Q5A, TI корпус Q5A (DQJ), 5 × 6 мм. 2026-11-14 — по PDF TI SLPS483 §7.2 (рисунок F1–F11) и §7.3 (трафарет).
# Нумерация — как у TI и символа Transistor_FET:CSD19534Q5A: 1–3 исток, 4 затвор, 5 сток (площадка + 4 «пальца»).
# У TI выводы справа (1 внизу); здесь повёрнуто на 180°: выводы слева, 1 вверху — те же номера на тех же местах корпуса.
# F4/F8 0,65–0,7 и F5/F9 0,62–0,67 при шаге 1,27 совместимы только при 0,65 / 0,62 → площадки 0,65 по шагу.
# F7 = 0,75 (0,7–0,8), F1 = 6,255 → наружные края ±3,1275; F10 = 4,95; F6 (палец) = 0,655; F11 = 4,51.
DQJ_PADS = [
    ('1', -2.7525, -1.905, 0.75, 0.65), ('2', -2.7525, -0.635, 0.75, 0.65), ('3', -2.7525, 0.635, 0.75, 0.65),
    ('4', -2.7525, 1.905, 0.75, 0.65),
    ('5', 2.8000, -1.905, 0.655, 0.65), ('5', 2.8000, -0.635, 0.655, 0.65), ('5', 2.8000, 0.635, 0.655, 0.65),
    ('5', 2.8000, 1.905, 0.655, 0.65),
]
DQJ_EP = (0.3250, 0, 4.295, 4.51)          # тело стока: x −1,8225 … 2,4725 (зазор до истоков 0,555)
# паста TI §7.3: окна стока 1,235 (ближе к истокам) и 1,585, высота 1,570, зазоры 0,5 и 0,62; выводы — 0,5 × 0,5
DQJ_PASTE = [(-0.7975, -1.095, 1.235, 1.57), (-0.7975, 1.095, 1.235, 1.57),
             (1.1125, -1.095, 1.585, 1.57), (1.1125, 1.095, 1.585, 1.57)] + \
            [(x, y, 0.5, 0.5) for _, x, y, _w, _h in DQJ_PADS]


def dqj(name):
    lines = [
        '(footprint "%s"' % name, '  (version 20241229)', '  (generator "mso74-gen")', '  (generator_version "9.0")',
        '  (layer "F.Cu")',
        '  (descr "TI VSONP-8 DQJ (Q5A) 5x6mm, CSD19534Q5A; pins 1-3 S, 4 G, 5 D (as TI and KiCad symbol). '
        'Pads per TI SLPS483 7.2/7.3 (F1-F11, stencil)")',
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
        lines.append('  (pad "%s" smd rect (at %s %s) (size %s %s) (layers "F.Cu" "F.Mask"))'
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
    p10 = [p for p in RJR_CU if p[0] == '10'][0]
    assert (p10[3], p10[4]) == (2.4, 0.4)


# BSP75N (Infineon HITFET, Data Sheet Rev.1.4, с. 2, рис. 2): 1 IN, 2 DRAIN, «3 + TAB SOURCE» — корпус на истоке.
# В KiCad есть только SOT-223-3_TabPin2 (корпус на выводе 2); берём его и переносим корпусную площадку на вывод 3.
# Аудит Codex C2-001: с TabPin2 корпус замкнул бы сток (клемму выхода) на GND в обход защиты.
TAB3 = {'SOT-223-3_TabPin3_BSP75N': 'Package_TO_SOT_SMD.pretty/SOT-223-3_TabPin2'}


def derive_tab3(fpdir, name, src):
    text = open(os.path.join(fpdir, src + '.kicad_mod'), encoding='utf-8').read()
    tab = '(pad "2" smd roundrect\n\t\t(at 3.15 0)\n\t\t(size 2 3.8)'
    assert text.count(tab) == 1, 'корпусная площадка SOT-223 не найдена'
    text = text.replace(tab, tab.replace('"2"', '"3"')).replace('SOT-223-3_TabPin2', name)
    text = text.replace('(descr "', '(descr "BSP75N: TAB = pin 3 (SOURCE) per Infineon BSP75N Rev.1.4 p.2; based on KiCad ', 1)
    return text


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
    for name, src in TAB3.items():
        with open(os.path.join(pretty, name + '.kicad_mod'), 'w', encoding='utf-8') as f:
            f.write(derive_tab3(fpdir, name, src))
    return set(FOOTPRINTS) | set(DERIVED) | set(TAB3)
