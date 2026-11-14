"""Свои символы (только то, чего нет в официальных библиотеках KiCad 9).

Каждый символ — с источником распиновки. Перед разводкой сверить с даташитом ещё раз.
"""
from sexp import Q, dump

FONT = ['effects', ['font', ['size', 1.27, 1.27]]]


def _prop(name, val, x, y, hide=False, just=None):
    eff = ['effects', ['font', ['size', 1.27, 1.27]]]
    if just:
        eff.append(['justify', just])
    if hide:
        eff.append(['hide', 'yes'])
    return ['property', Q(name), Q(val), ['at', x, y, 0], eff]


def _pin(typ, x, y, ang, name, num, length=2.54):
    return ['pin', typ, 'line', ['at', x, y, ang], ['length', length],
            ['name', Q(name), FONT], ['number', Q(num), FONT]]


def ic(name, ref, desc, fp, datasheet, left, right, top=(), bottom=(), w=15.24):
    """left/right/top/bottom: списки (номер, имя, тип) сверху вниз / слева направо."""
    n = max(len(left), len(right), 1)
    h = (n + 1) * 2.54
    y0 = h / 2
    body = ['symbol', Q(name + '_0_1'),
            ['rectangle', ['start', -w / 2, y0], ['end', w / 2, -y0], ['stroke', ['width', 0.254], ['type', 'default']],
             ['fill', ['type', 'background']]]]
    pins = ['symbol', Q(name + '_1_1')]
    for i, (num, nm, typ) in enumerate(left):
        pins.append(_pin(typ, -w / 2 - 2.54, round(y0 - 2.54 * (i + 1), 2), 0, nm, num))
    for i, (num, nm, typ) in enumerate(right):
        pins.append(_pin(typ, w / 2 + 2.54, round(y0 - 2.54 * (i + 1), 2), 180, nm, num))
    for i, (num, nm, typ) in enumerate(top):
        pins.append(_pin(typ, round(-2.54 * (len(top) - 1) / 2 + 2.54 * i, 2), y0 + 2.54, 270, nm, num))
    for i, (num, nm, typ) in enumerate(bottom):
        pins.append(_pin(typ, round(-2.54 * (len(bottom) - 1) / 2 + 2.54 * i, 2), -y0 - 2.54, 90, nm, num))
    return ['symbol', Q(name), ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
            _prop('Reference', ref, -w / 2, y0 + 1.27, just='left'),
            _prop('Value', name, -w / 2, -y0 - 1.27, just='left'),
            _prop('Footprint', fp, 0, 0, hide=True),
            _prop('Datasheet', datasheet, 0, 0, hide=True),
            _prop('Description', desc, 0, 0, hide=True),
            body, pins]


SYMBOLS = [
    # Распиновка: TI SNVSBR8E (LMQ61460, pin-to-pin с LM61460), табл. «Pin Functions», RJR VQFN-HR-14 — сверено 2026-11-14.
    ic('LM61460', 'U', '36 В, 6 А синхронный понижающий, VQFN-HR-14 (RJR)',
       'mso74:Texas_RJR_VQFN-HR-14_3.5x4mm', 'https://www.ti.com/lit/gpn/lm61460',
       left=[('8', 'VIN1', 'power_in'), ('12', 'VIN2', 'power_in'), ('7', 'EN/SYNC', 'input'), ('6', 'RT', 'passive'),
             ('1', 'BIAS', 'power_in'), ('2', 'VCC', 'power_out')],
       right=[('14', 'CBOOT', 'passive'), ('13', 'RBOOT', 'passive'), ('10', 'SW', 'power_out'),
              ('4', 'FB', 'input'), ('5', 'PGOOD', 'open_collector')],
       bottom=[('3', 'AGND', 'power_in'), ('9', 'PGND1', 'power_in'), ('11', 'PGND2', 'power_in')], w=17.78),
]


def write(path):
    doc = ['kicad_symbol_lib', ['version', '20241209'], ['generator', Q('mso74-gen')], ['generator_version', Q('9.0')]] + SYMBOLS
    with open(path, 'w', encoding='utf-8') as f:
        f.write(dump(doc) + '\n')
