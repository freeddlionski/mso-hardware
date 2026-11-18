"""Лист «RS-485 и RS-232»: Modbus (THVD2410, ±70 В) и терминал Vendotek (MAX3232 от 3,3 В).
Каждая клемма переживает +24 В: RS-485 — сам трансивер (±70 В), TVS 36 В срабатывает только на импульсах;
терминатор — последовательно со 100 нФ (AC); RS-232 — 2,2 кОм (TX) / 1 кОм (RX) 2512 + SMAJ8.0CA со стороны микросхемы.
"""
from sheet_power import C, R, FP, two

TERM3 = 'mso74:KANGNEX_WJ15EDGRC_1x03_P3.81mm_Drill1.4'


def build(proj):
    from kisch import Sheet
    sh = Sheet(proj, 'comm', 'RS-485 и RS-232', paper='A3')

    # ---------- RS-485 ----------
    x, y = 127.0, 76.2
    sh.text('RS-485 (Modbus RTU 9600): THVD2410 от 3,3 В, защита шины ±70 В; DE/RE — GPIO 38 (RTS UART1, PINOUT.md).', (20.32, 30.48), 1.5)
    u = sh.part('Interface_UART:THVD1450D', 'U', 'THVD2410DR', (x, y), lcsc='C1849398', mpn='THVD2410DR',
                fields={'Примечание': 'символ THVD1450D — распиновка THVD2410 та же (R, RE, DE, D, GND, A, B, VCC)'})
    sh.connect(u, {'RO': 'RS485_RX', '~{RE}': 'RS485_DE', 'DE': 'RS485_DE', 'DI': 'RS485_TX', 'GND': 'GND',
                   'VCC': '+3V3', 'A': 'RS485_A', 'B': 'RS485_B'})
    C(sh, '100n', x - 63.5, y - 10.16, '+3V3', 'GND')
    R(sh, '10k', x - 63.5, y, 'RS485_DE', 'GND')                       # при сбросе — приём
    sh.text('DE: 10 кОм на землю — после сброса трансивер слушает шину', (x - 81.28, y + 7.62))
    # светодиоды активности: линия в «0» — светится (ток ~1,5 мА с вывода)
    R(sh, '1k', x - 63.5, y + 17.78, '+3V3', 'LED485_TX')
    p = sh.part('Device:LED', 'D', 'красный TX', (x - 22.86, y + 17.78), rot=180, fp=FP['LED0603'])
    sh.connect(p, {'A': 'LED485_TX', 'K': 'RS485_TX'})
    R(sh, '1k', x - 63.5, y + 27.94, '+3V3', 'LED485_RX')
    p = sh.part('Device:LED', 'D', 'зелёный RX', (x - 22.86, y + 27.94), rot=180, fp=FP['LED0603'])
    sh.connect(p, {'A': 'LED485_RX', 'K': 'RS485_RX'})

    xa = 215.9
    two(sh, 'Device:D_TVS', 'D', 'SMAJ36CA', xa, y - 10.16, 'RS485_A', 'GND', fp='Diode_SMD:D_SMA', mpn='SMAJ36CA')
    two(sh, 'Device:D_TVS', 'D', 'SMAJ36CA', xa, y, 'RS485_B', 'GND', fp='Diode_SMD:D_SMA', mpn='SMAJ36CA')
    # аудит 2, п. 9: терминатор 120 Ом последовательно с 100 нФ (AC-терминатор): постоянного тока нет, +24 В на A/B резистор не греет.
    # τ = 12 мкс при длительности бита 104 мкс (9600) — допустимо
    R(sh, '120', xa, y + 15.24, 'RS485_A', 'R485_T1', 'R0805')
    C(sh, '100n 100V', xa, y + 25.4, 'R485_T1', 'R485_T2', 'C0805')
    jp = sh.part('Connector_Generic:Conn_01x02', 'JP', 'Терминатор 120 Ом', (xa + 40.64, y + 30.48),
                 fp='Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical', fields={'Примечание': 'перемычка-джампер'})
    sh.connect(jp, {'1': 'R485_T2', '2': 'RS485_B'})
    # смещение (не устанавливать: у THVD2410 встроенный failsafe)
    R(sh, '680 DNP', xa, y + 45.72, '+3V3', 'RS485_A').dnp = True
    R(sh, '680 DNP', xa, y + 55.88, 'RS485_B', 'GND').dnp = True
    j = sh.part('Connector_Generic:Conn_01x03', 'J', 'RS-485: A / B / GND', (xa + 81.28, y), fp=TERM3,
                fields={'Примечание': 'не рядом с клеммой питания 24 В', 'Шелкография': 'A, B, GND'})
    sh.connect(j, {'1': 'RS485_A', '2': 'RS485_B', '3': 'GND'})

    # ---------- RS-232 Vendotek ----------
    # 14.11: MAX13223E (±70 В) снят — на складе LCSC нет («надо доступные компоненты», Павел).
    # MAX3232EIDR (TI, ходовой) + защита на каждой линии: 2,2 кОм 2512 последовательно и двунаправленный TVS SMAJ8.0CA
    # со стороны микросхемы. +32 В на клемме: ток ≈ (32 − 9,8) / 2,2k ≈ 10 мА, 0,23 Вт в резисторе на 1 Вт;
    # на выводе ≤ 9,8 В (пробой SMAJ8.0CA) — ниже предела выхода передатчика ±13,2 В и входа приёмника ±25 В
    # (аудит 1, п. 13: прежний TVS без резистора этого не держал). Сигнал: ±5,4 В передатчика на вход терминала 5 кОм
    # через 2,2 кОм — ≈ ±3,7 В (порог приёмника RS-232 — до 2,4 В).
    x, y = 127.0, 195.58
    sh.text('RS-232 терминал Vendotek (115200): MAX3232E от 3,3 В; линии: 2,2 кОм 2512 + SMAJ8.0CA — +32 В на клемме безопасно.',
            (20.32, y - 33.02), 1.5)
    u = sh.part('Interface_UART:MAX3232', 'U', 'MAX3232EIDR', (x, y), fp='Package_SO:SOIC-16_3.9x9.9mm_P1.27mm',
                mpn='MAX3232EIDR')
    sh.connect(u, {'VCC': '+3V3', 'GND': 'GND', 'C1+': 'VTK_C1P', 'C1-': 'VTK_C1N', 'C2+': 'VTK_C2P', 'C2-': 'VTK_C2N',
                   'VS+': 'VTK_VSP', 'VS-': 'VTK_VSN', 'T1IN': 'VTK_TX', 'R1OUT': 'VTK_RX', 'T1OUT': 'VTK_TX_U', 'R1IN': 'VTK_RX_U',
                   'T2IN': 'GND'},
               nc=['T2OUT', 'R2IN', 'R2OUT'])
    xc = x - 71.12
    C(sh, '100n', xc, y - 20.32, 'VTK_C1P', 'VTK_C1N')       # MAX3232 при VCC 3,0–3,6 В: все четыре — 0,1 мкФ
    C(sh, '100n', xc, y - 10.16, 'VTK_C2P', 'VTK_C2N')
    C(sh, '100n', xc, y, 'VTK_VSP', 'GND')
    C(sh, '100n', xc, y + 10.16, 'VTK_VSN', 'GND')
    C(sh, '100n', xc, y + 20.32, '+3V3', 'GND')
    xp = x + 50.8
    two(sh, 'Device:D_TVS', 'D', 'SMAJ8.0CA', xp, y - 10.16, 'VTK_TX_U', 'GND', fp='Diode_SMD:D_SMA', mpn='SMAJ8.0CA')
    two(sh, 'Device:D_TVS', 'D', 'SMAJ8.0CA', xp, y + 10.16, 'VTK_RX_U', 'GND', fp='Diode_SMD:D_SMA', mpn='SMAJ8.0CA')
    R(sh, '2.2k 1W', xp + 20.32, y - 10.16, 'VTK_TX_U', 'VTK_TX_T', 'R2512')
    # приём: 1 кОм (аудит 17.11) — с ёмкостью SMAJ8.0CA (~1 нФ) 2,2 кОм заваливали фронты на 115200; +32 В: 22 мА, 0,49 Вт
    R(sh, '1k 1W', xp + 20.32, y + 10.16, 'VTK_RX_U', 'VTK_RX_T', 'R2512')
    xa = 215.9
    j = sh.part('Connector_Generic:Conn_01x03', 'J', 'Vendotek RS-232: TXD / RXD / GND', (xa + 40.64, y), fp=TERM3,
                fields={'Примечание': 'TXD — выход платы (к RXD терминала), RXD — вход платы', 'Шелкография': 'TXD, RXD, GND'})
    sh.connect(j, {'1': 'VTK_TX_T', '2': 'VTK_RX_T', '3': 'GND'})
    return sh
