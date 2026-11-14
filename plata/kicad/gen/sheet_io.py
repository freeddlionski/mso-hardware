"""Лист «MDB и входы»: купюроприёмник MDB, импульсные входы монетника и купюрника, блокировка монетника, сервисная кнопка.

Защита от +24 В на любой сигнальной линии: клемма → самовосст. предохранитель 50 мА → TVS на землю (за предохранителем)
→ резистор → микросхема/GPIO. При +24 В TVS открывается, ток через предохранитель резко растёт, он отключается.
Распиновка MDB и токи — mso-firmware/docs/MDB.md; ряды Mini-Fit: 1-2-3 и 4-5-6 (площадки посадочного места KiCad).
"""
from sheet_power import C, R, FP, two

TERM = {n: 'Connector_Phoenix_MC:PhoenixContact_MC_1,5_%d-G-3.81_1x%02d_P3.81mm_Horizontal' % (n, n) for n in (2, 3, 4)}
PTC50 = dict(fp='Fuse:Fuse_1206_3216Metric')


def guard(sh, x, y, outer, inner, tvs='SMAJ5.0A', ptc='50mA удерж.'):
    """клемма(outer) → PTC → inner; TVS inner → GND."""
    two(sh, 'Device:Polyfuse', 'F', ptc, x, y, outer, inner, **PTC50)
    two(sh, 'Device:D_TVS', 'D', tvs, x, y + 10.16, inner, 'GND', fp='Diode_SMD:D_SMA', mpn=tvs)


def clamp(sh, x, y, net):
    """BAT54S: вывод к 3,3 В и к земле."""
    d = sh.part('Diode:BAT54S', 'D', 'BAT54S', (x, y), mpn='BAT54S')
    sh.connect(d, {'A': 'GND', 'K': '+3V3', 'COM': net})


def pulse_input(sh, x, y, term_net, gpio_net, tag):
    """Оптрон: +12 В → 2,2 кОм → светодиод → клемма → открытый коллектор аппарата → минус."""
    a, k_in, c = tag + '_LA', term_net, tag + '_C'
    R(sh, '2.2k', x, y, '+12V', a)
    o = sh.part('Isolator:PC817', 'U', 'EL357N(C)', (x + 38.1, y + 2.54), fp='Package_SO:SOP-4_3.8x4.1mm_P2.54mm', mpn='EL357N(C)-G')
    sh.connect(o, {'1': a, '2': k_in, '4': c, '3': 'GND'})
    d = sh.part('Diode:1N4148W', 'D', '1N4148W', (x, y + 12.7), mpn='1N4148W')
    sh.connect(d, {'A': k_in, 'K': a})          # обратное напряжение на светодиоде оптрона ≤ 0,7 В
    R(sh, '10k', x + 76.2, y - 7.62, '+3V3', c)
    R(sh, '1k', x + 76.2, y + 2.54, c, gpio_net)
    C(sh, '10n', x + 76.2, y + 12.7, gpio_net, 'GND')


def build(proj):
    from kisch import Sheet
    sh = Sheet(proj, 'io', 'MDB и входы', paper='A3')

    # ---------- MDB ----------
    x, y = 40.64, 50.8
    sh.text('MDB (CashCode): 1 +24 В, 2 минус, 4 Master Receive, 5 Master Transmit, 6 общий сигналов. Передача ~10–13 мА от 5 В.',
            (20.32, 25.4), 1.5)
    b = sh.part('74xGxx:74AHCT1G125', 'U', '74AHCT1G125', (x + 12.7, y), fp='Package_TO_SOT_SMD:SOT-23-5', mpn='SN74AHCT1G125DBVR')
    sh.connect(b, {'1': 'GND', '2': 'MDB_TX', '4': 'MDB_TX_B', '5': '+5V', '3': 'GND'})
    C(sh, '100n', x - 10.16, y + 20.32, '+5V', 'GND')
    R(sh, '120', x + 50.8, y, 'MDB_TX_B', 'MDB_TX_P', 'R0805')
    guard(sh, x + 88.9, y, 'MDB_TX_L', 'MDB_TX_P')
    # приём
    guard(sh, x + 88.9, y + 30.48, 'MDB_RX_L', 'MDB_RX_P')
    R(sh, '1k', x + 50.8, y + 30.48, 'MDB_RX_P', 'MDB_RX')
    R(sh, '4.7k', x + 50.8, y + 40.64, '+3V3', 'MDB_RX')
    clamp(sh, x + 12.7, y + 45.72, 'MDB_RX')
    j = sh.part('Connector_Generic:Conn_02x03_Odd_Even', 'J', 'MDB Mini-Fit Jr 2×3', (x + 142.24, y + 15.24),
                fp='Connector_Molex:Molex_Mini-Fit_Jr_5566-06A_2x03_P4.20mm_Vertical', mpn='Molex 5566-06A')
    sh.connect(j, {'1': 'MDB_24V', '2': 'GND', '4': 'MDB_RX_L', '5': 'MDB_TX_L', '6': 'GND'}, nc=['3'])

    # ---------- импульсные входы ----------
    x, y = 40.64, 129.54
    sh.text('Импульсные входы: аппарат замыкает «импульс» на минус (открытый коллектор), 14 мс / 14 мс. Оптрон от +12 В.',
            (20.32, y - 17.78), 1.5)
    pulse_input(sh, x, y, 'COIN_IN', 'COIN_PULSE', 'CI')
    pulse_input(sh, x, y + 30.48, 'BILL_IN', 'BILL_PULSE', 'BI')
    two(sh, 'Device:Polyfuse', 'F', '1A удерж.', x + 129.54, y - 12.7, '+12V', '+12V_T', fp='Fuse:Fuse_1812_4532Metric')
    sh.text('+12V_T — питание монетника и купюрника на клеммы', (x + 111.76, y - 22.86))

    # блокировка монетника: ключ на минус, сток выдерживает 60 В
    x2, y2 = 40.64, 205.74
    sh.text('Блокировка монетника: 2N7002 на минус (до 24 В / 100 мА), при сбросе выключена.', (20.32, y2 - 12.7), 1.5)
    R(sh, '100', x2, y2, 'COIN_INH', 'Q_INH_G')
    R(sh, '100k', x2, y2 + 10.16, 'Q_INH_G', 'GND')
    q = sh.part('Transistor_FET:2N7002', 'Q', '2N7002', (x2 + 33.02, y2 + 2.54), mpn='2N7002')
    sh.connect(q, {'G': 'Q_INH_G', 'S': 'GND', 'D': 'COIN_INH_D'})
    two(sh, 'Device:Polyfuse', 'F', '100mA удерж.', x2 + 71.12, y2, 'COIN_INH_D', 'COIN_INH_T', **PTC50)

    # сервисная кнопка
    x3, y3 = 40.64, 246.38
    sh.text('Сервисная кнопка (GPIO 20): кнопка на плате и клемма выносной кнопки.', (20.32, y3 - 12.7), 1.5)
    guard(sh, x3 + 88.9, y3, 'SVC_T', 'SVC_P')
    R(sh, '1k', x3 + 50.8, y3, 'SVC_P', 'SERVICE_BTN')
    R(sh, '10k', x3 + 50.8, y3 + 10.16, '+3V3', 'SERVICE_BTN')
    clamp(sh, x3 + 12.7, y3 + 7.62, 'SERVICE_BTN')
    two(sh, 'Switch:SW_Push', 'SW', 'СЕРВИС', x3 + 12.7, y3 + 22.86, 'SERVICE_BTN', 'GND', fp='Button_Switch_SMD:SW_SPST_TL3342')

    # клеммы
    xt = 279.4
    sh.text('Клеммы 3,81 мм (разъёмные). Подписи каждого контакта — на шелкографии.', (xt - 20.32, 96.52))
    j = sh.part('Connector_Generic:Conn_01x04', 'J', 'Монетник: +12V / GND / ИМП / БЛОК', (xt, 116.84), fp=TERM[4])
    sh.connect(j, {'1': '+12V_T', '2': 'GND', '3': 'COIN_IN', '4': 'COIN_INH_T'})
    j = sh.part('Connector_Generic:Conn_01x04', 'J', 'Купюрник имп.: +24V / +12V / GND / ИМП', (xt, 152.4), fp=TERM[4])
    sh.connect(j, {'1': 'MDB_24V', '2': '+12V_T', '3': 'GND', '4': 'BILL_IN'})
    j = sh.part('Connector_Generic:Conn_01x02', 'J', 'Сервис: КН / GND', (xt, 246.38), fp=TERM[2])
    sh.connect(j, {'1': 'SVC_T', '2': 'GND'})
    return sh
