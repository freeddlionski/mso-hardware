"""Лист «MDB и входы»: купюроприёмник MDB, импульсные входы монетника и купюрника, блокировка монетника, сервисная кнопка.

Защита от +24 В на любой сигнальной линии: клемма → самовосст. предохранитель 50 мА → TVS на землю (за предохранителем)
→ резистор → микросхема/GPIO. При +24 В TVS открывается, ток через предохранитель резко растёт, он отключается.
Распиновка MDB и токи — mso-firmware/docs/MDB.md; ряды Mini-Fit: 1-2-3 и 4-5-6 (площадки посадочного места KiCad).
"""
from sheet_power import C, R, FP, tvs, two

TERM = {n: 'Connector_Phoenix_MC:PhoenixContact_MC_1,5_%d-G-3.81_1x%02d_P3.81mm_Horizontal' % (n, n) for n in (2, 3, 4, 5, 6)}
PTC50 = dict(fp='Fuse:Fuse_1206_3216Metric')


def blocked_input(sh, x, y, term, gpio, tag, pullup='10k'):
    """Вход «на минус» (сухой контакт, открытый коллектор), переживает +24 В без тока в плату (аудит 2, пп. 5, 10 и доп.):
    клемма — TVS 28 В на землю (только импульсы) — PTC 50 мА — диод Шоттки BAT46W (катод к клемме) — 330 Ом — вход.
    +24 В на клемме запирает диод: ток не идёт ни в шину 3,3 В, ни в выключенную плату. «0»: 0,33 мА × 330 Ом + диод ≈ 0,5 В."""
    tvs(sh, 'SMAJ28A', x + 76.2, y + 10.16, term)
    two(sh, 'Device:Polyfuse', 'F', '50mA удерж.', x + 76.2, y, term, tag + '_P', **PTC50)
    d = sh.part('Device:D_Schottky', 'D', 'BAT46W', (x + 38.1, y), fp='Diode_SMD:D_SOD-123', mpn='BAT46W')
    sh.connect(d, {'K': tag + '_P', 'A': tag + '_N'})
    R(sh, '330', x, y, tag + '_N', gpio)
    R(sh, pullup, x, y + 10.16, '+3V3', gpio)
    clamp(sh, x - 25.4, y + 7.62, gpio)


def clamp(sh, x, y, net):
    """BAT54S: вывод к 3,3 В и к земле."""
    d = sh.part('Diode:BAT54S', 'D', 'BAT54S', (x, y), mpn='BAT54S')
    sh.connect(d, {'A': 'GND', 'K': '+3V3', 'COM': net})


def pulse_input(sh, x, y, term_net, gpio_net, tag):
    """Оптрон: +12 В → 2,2 кОм → светодиод → клемма → открытый коллектор аппарата → минус."""
    a, k_in, c = tag + '_LA', term_net, tag + '_C'
    R(sh, '1.5k', x, y, '+12V', a)            # ~7 мА: запас по CTR оптрона при просадке 12 В
    o = sh.part('Isolator:PC817', 'U', 'EL357N(C)', (x + 38.1, y + 2.54), fp='Package_SO:SOP-4_3.8x4.1mm_P2.54mm', mpn='EL357N(C)-G')
    sh.connect(o, {'1': a, '2': tag + '_K', '4': c, '3': 'GND'})
    # аудит 2, п. 5: диод последовательно (катод к клемме) — +24 В на клемме его запирает, тока в +12 В нет
    d = sh.part('Diode:1N4148W', 'D', '1N4148W', (x, y + 12.7), mpn='1N4148W')
    sh.connect(d, {'A': tag + '_K', 'K': k_in})
    tvs(sh, 'SMAJ28A', x, y + 22.86, k_in)
    # ток светодиода (12 − 1,2 − 0,7) / 1,5 кОм ≈ 6,7 мА
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
    # 150 Ом (как в ТЗ): при +24 В на клемме TVS держит ~8 В, ток в выход буфера ≤ ~17 мА; рабочий ток ~10 мА (CashCode: 220 Ом внутри)
    # аудит 2, п. 10: диод Шоттки после буфера — +24 В на линии его запирает, в выход 74AHCT1G125 ток не идёт.
    # Рабочий ток (5 − 0,4 − 1,2) / (150 + 220 внутри CashCode) ≈ 9 мА
    d = sh.part('Device:D_Schottky', 'D', 'BAT46W', (x + 38.1, y), fp='Diode_SMD:D_SOD-123', mpn='BAT46W')
    sh.connect(d, {'A': 'MDB_TX_B', 'K': 'MDB_TX_D'})
    R(sh, '150', x + 63.5, y, 'MDB_TX_D', 'MDB_TX_P', 'R0805')
    two(sh, 'Device:Polyfuse', 'F', '50mA удерж.', x + 101.6, y, 'MDB_TX_P', 'MDB_TX_L', **PTC50)
    tvs(sh, 'SMAJ28A', x + 101.6, y + 10.16, 'MDB_TX_L')
    # приём: купюрник замыкает линию на общий; подтяжка 10 кОм (при 4,7 кОм падение на диоде и резисторе поднимает «0»)
    blocked_input(sh, x + 25.4, y + 30.48, 'MDB_RX_L', 'MDB_RX', 'MDBRX')
    j = sh.part('Connector_Generic:Conn_02x03_Odd_Even', 'J', 'MDB Mini-Fit Jr 2×3', (x + 142.24, y + 15.24),
                fp='Connector_Molex:Molex_Mini-Fit_Jr_5566-06A_2x03_P4.20mm_Vertical', mpn='Molex 5566-06A',
                fields={'Шелкография': 'MDB; 1 +24V, 2 GND, 4 RX, 5 TX, 6 COM'})
    sh.connect(j, {'1': 'MDB_24V', '2': 'GND', '4': 'MDB_RX_L', '5': 'MDB_TX_L', '6': 'GND'}, nc=['3'])

    # ---------- импульсные входы ----------
    x, y = 40.64, 129.54
    sh.text('Импульсные входы: аппарат замыкает «импульс» на минус (открытый коллектор), 14 мс / 14 мс. Оптрон от +12 В.',
            (20.32, y - 17.78), 1.5)
    pulse_input(sh, x, y, 'COIN_IN', 'COIN_PULSE', 'CI')
    pulse_input(sh, x, y + 30.48, 'BILL_IN', 'BILL_PULSE', 'BI')
    two(sh, 'Device:Polyfuse', 'F', '1A удерж.', x + 129.54, y - 12.7, '+12V', '+12V_F', fp='Fuse:Fuse_1812_4532Metric')
    # аудит 2, п. 6: +24 В на клемме +12 В не попадёт в шину 12 В и выход LMR51430 (падение ~0,4 В)
    d = sh.part('Device:D_Schottky', 'D', 'SS34', (x + 160.02, y - 12.7), fp='Diode_SMD:D_SMA', mpn='SS34')
    sh.connect(d, {'A': '+12V_F', 'K': '+12V_T'})
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
    blocked_input(sh, x3 + 25.4, y3, 'SVC_T', 'SERVICE_BTN', 'SVC')
    two(sh, 'Switch:SW_Push', 'SW', 'СЕРВИС', x3 + 12.7, y3 + 22.86, 'SERVICE_BTN', 'GND', fp='Button_Switch_SMD:SW_SPST_TL3342')

    # клеммы
    xt = 279.4
    sh.text('Клеммы 3,81 мм (разъёмные). Подписи каждого контакта — на шелкографии.', (xt - 20.32, 96.52))
    j = sh.part('Connector_Generic:Conn_01x04', 'J', 'Монетник: +12V / GND / ИМП / БЛОК', (xt, 116.84), fp=TERM[4],
                 fields={'Шелкография': 'МОНЕТНИК: +12V, GND, ИМП, БЛОК'})
    sh.connect(j, {'1': '+12V_T', '2': 'GND', '3': 'COIN_IN', '4': 'COIN_INH_T'})
    j = sh.part('Connector_Generic:Conn_01x04', 'J', 'Купюрник имп.: +24V / +12V / GND / ИМП', (xt, 152.4), fp=TERM[4],
                 fields={'Шелкография': 'КУПЮРНИК: +24V, +12V, GND, ИМП'})
    sh.connect(j, {'1': 'MDB_24V', '2': '+12V_T', '3': 'GND', '4': 'BILL_IN'})
    j = sh.part('Connector_Generic:Conn_01x02', 'J', 'Сервис: КН / GND', (xt, 246.38), fp=TERM[2],
                 fields={'Шелкография': 'СЕРВИС: КН, GND'})
    sh.connect(j, {'1': 'SVC_T', '2': 'GND'})
    return sh
