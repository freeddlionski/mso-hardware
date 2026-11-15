"""Правила трассировки платы МСО74 → в mso74-plata.kicad_pro (build.py) и в зоны (pcb_route.py).

Источник чисел — аудит Codex df4bb5c §5.2–5.4 (plata/audit/codex_audit_df4bb5c.md): JLC04161H-7628, 4 слоя 1,6 мм,
наружная медь 1 oz, внутренняя 0,5 oz.
Слои: F.Cu — детали, силовые петли, пары Ethernet/USB; In1.Cu — сплошная GND; In2.Cu — области питания (+24V_P слева,
+3V3 справа) и GND; B.Cu — вторичные сигналы и GND.
"""

# класс: (дорожка, зазор, via диаметр, via отверстие), мм
# Зазор цепей 24–35 В — 0,30 мм: IPC-2221B табл. 6-1, B4 (наружный слой под маской), 31–50 В — 0,13 мм; запас ×2.
# (Codex предлагал 0,50 как запас, но у U1/U2–U4 выводы сами стоят на 0,25–0,375 мм — трассировщику не выйти из площадки.)
# Площадки одной микросхемы между собой — по её посадочному месту (mso74-plata.kicad_dru).
CLASSES = {
    'Default': (0.20, 0.20, 0.60, 0.30),
    'P24_MAIN': (4.00, 0.30, 0.60, 0.30),   # вход 6 А до eFuse: 4 мм (IPC-2221, ΔT 10 °C, 1 oz; Codex §5.2, R-008)
    'P24': (1.00, 0.30, 0.60, 0.30),        # +24V_P (основное — плоскость In2) и выходы 24 В на клеммы до 1,5 А
    'LCD': (3.00, 0.25, 0.60, 0.30),        # табло 5 А: SW→L→COUT→J3/J4 — 3 мм (Codex §5.2, R-008)
    'SW': (1.00, 0.25, 0.60, 0.30),         # узлы SW LMR51430 (короткие)
    'PWR': (0.60, 0.15, 0.60, 0.30),        # +12V, +5V, +3V3 магистрали, выходы расширителя; зазор 0,15 — шаг 0,4 мм у U22/U10
    # Fine via назначен классам, а не только меню: KiCad экспортирует его в DSN use_via.
    # 0,45/0,20 — кольцо 0,125 мм; для fanout QFN и копий USB-C. Силовые классы сохраняют 0,60/0,30.
    'ETH': (0.24, 0.20, 0.45, 0.20),        # пары Ethernet (100 Ом: W 0,24 / S 0,20 — по стеку JLC 7628)
    'USB': (0.29, 0.20, 0.45, 0.20),        # USB D+/D− (90 Ом: W 0,29 / S 0,20)
}

# Шаблоны: у локальных цепей имя с путём листа («/Лист/ИМЯ»), у глобальных — без; пишем оба варианта (Codex R-002)
def _both(cls, *names):
    return [(cls, n) for name in names for n in (name, '*/' + name)]


PATTERNS = (
    _both('P24_MAIN', 'VIN_RAW', 'VIN_B', 'VIN_F') +
    _both('P24', '+24V_P', 'VTK_24V', 'MDB_24V', 'EXT_24V') +
    _both('LCD', '+5V_LCD1', '+5V_LCD2', 'LCD1_SW', 'LCD2_SW') +
    _both('SW', 'P12_SW', 'P5_SW', 'P3_SW') +
    _both('PWR', '+12V', '+12V_F', '+12V_T', '+5V', '+3V3', '+3V3A', 'EXT_D?', 'COIN_INH_D', 'SW_VCORE') +
    _both('ETH', 'ETH_TX?', 'ETH_RD?', 'ETH_RX?', 'LNK_?_?', 'SW_TX??', 'SW_RX??') +
    _both('USB', 'USB_DP', 'USB_DM')
)

# ограничения платы (JLC, Codex §5.2): переход 0,3/0,6; 0,2-мм отверстия ESP32 допустимы; медь до кромки ≥ 0,3 мм
RULES = {
    'min_clearance': 0.15, 'min_track_width': 0.15, 'min_via_diameter': 0.45, 'min_via_annular_width': 0.1,
    'min_through_hole_diameter': 0.2, 'min_hole_to_hole': 0.2, 'min_hole_clearance': 0.2,
    'min_copper_edge_clearance': 0.3, 'min_microvia_diameter': 0.2, 'min_microvia_drill': 0.1,
    'min_silk_clearance': 0.0, 'min_resolved_spokes': 1, 'min_text_height': 0.8, 'min_text_thickness': 0.08, 'solder_mask_to_copper_clearance': 0.0,
}

# области In2.Cu (координаты платы, мм): x0, y0, x1, y1
IN2 = [('+24V_P', (0.5, 0.5, 82.0, 119.5)), ('+3V3', (82.5, 0.5, 239.5, 119.5))]


def project_json():
    classes = []
    for i, (name, (w, cl, vd, vdr)) in enumerate(CLASSES.items()):
        classes.append({
            'name': name, 'clearance': cl, 'track_width': w, 'via_diameter': vd, 'via_drill': vdr,
            'diff_pair_width': w, 'diff_pair_gap': 0.20, 'diff_pair_via_gap': 0.25,
            'microvia_diameter': 0.3, 'microvia_drill': 0.1, 'bus_width': 12, 'wire_width': 6, 'line_style': 0,
            'pcb_color': 'rgba(0, 0, 0, 0.000)', 'schematic_color': 'rgba(0, 0, 0, 0.000)',
            'priority': 2147483647 if name == 'Default' else i,
        })
    net = {'classes': classes, 'meta': {'version': 4}, 'net_colors': None, 'netclass_assignments': None,
           'netclass_patterns': [{'netclass': c, 'pattern': p} for c, p in PATTERNS]}
    board = {'design_settings': {'rules': RULES,
                                 'track_widths': [0.0, 0.2, 0.25, 0.6, 1.0, 2.0, 2.5],
                                 'via_dimensions': [{'diameter': 0.0, 'drill': 0.0}, {'diameter': 0.6, 'drill': 0.3}, {'diameter': 0.45, 'drill': 0.2}]}}
    return net, board


def apply_to_pro(pro):
    """Записать классы и правила в .kicad_pro (pcbnew.SaveBoard перезаписывает его значениями по умолчанию)."""
    import json
    import os
    d = json.load(open(pro, encoding='utf-8')) if os.path.exists(pro) else {}
    d['net_settings'], board = project_json()
    d.setdefault('board', {}).setdefault('design_settings', {}).update(board['design_settings'])
    with open(pro, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    with open(os.path.splitext(pro)[0] + '.kicad_dru', 'w', encoding='utf-8') as f:
        f.write(DRU)


DRU = """(version 1)
(rule "площадки одного корпуса — по посадочному месту"
  (condition "A.Type == 'Pad' && B.Type == 'Pad' && A.Parent == B.Parent")
  (constraint clearance (min 0.15mm)))
"""
