"""Лист «RS-485 и RS-232»: Modbus (THVD2410, ±70 В) и терминал Vendotek (MAX3232 от 3,3 В).
Каждая клемма переживает +24 В: RS-485 — сам трансивер (±70 В), TVS 36 В срабатывает только на импульсах;
терминатор — через самовосстанавливающийся предохранитель; RS-232 — предохранитель 50 мА + TVS 15 В на каждой линии.
"""
from sheet_power import C, R, FP, two

TERM3 = 'Connector_Phoenix_MC:PhoenixContact_MC_1,5_3-G-3.81_1x03_P3.81mm_Horizontal'


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
    p = sh.part('Device:LED', 'D', 'жёлтый TX', (x - 22.86, y + 17.78), rot=180, fp=FP['LED0603'])
    sh.connect(p, {'A': 'LED485_TX', 'K': 'RS485_TX'})
    R(sh, '1k', x - 63.5, y + 27.94, '+3V3', 'LED485_RX')
    p = sh.part('Device:LED', 'D', 'зелёный RX', (x - 22.86, y + 27.94), rot=180, fp=FP['LED0603'])
    sh.connect(p, {'A': 'LED485_RX', 'K': 'RS485_RX'})

    xa = 215.9
    two(sh, 'Device:D_TVS', 'D', 'SMAJ36CA', xa, y - 10.16, 'RS485_A', 'GND', fp='Diode_SMD:D_SMA', mpn='SMAJ36CA')
    two(sh, 'Device:D_TVS', 'D', 'SMAJ36CA', xa, y, 'RS485_B', 'GND', fp='Diode_SMD:D_SMA', mpn='SMAJ36CA')
    # терминатор 120 Ом через перемычку и предохранитель 50 мА (при +24 В на A/B резистор не сгорит)
    R(sh, '120', xa, y + 15.24, 'RS485_A', 'R485_T1', 'R0805')
    two(sh, 'Device:Polyfuse', 'F', '50mA удерж.', xa, y + 25.4, 'R485_T1', 'R485_T2', fp='Fuse:Fuse_1206_3216Metric')
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
    # аудит 1, п. 13: TVS не удерживал линии ниже ±13,2 В предела MAX3232 → MAX13223E, линии выдерживают ±70 В
    x, y = 127.0, 195.58
    sh.text('RS-232 терминал Vendotek (115200): MAX13223E от 3,3 В, линии T1OUT/R1IN выдерживают ±70 В — внешняя защита не нужна.',
            (20.32, y - 33.02), 1.5)
    u = sh.part('mso74:MAX13223E', 'U', 'MAX13223EEUP+', (x, y), mpn='MAX13223EEUP+')
    sh.connect(u, {'VCC': '+3V3', 'GND': 'GND', 'C1+': 'VTK_C1P', 'C1-': 'VTK_C1N', 'C2+': 'VTK_C2P', 'C2-': 'VTK_C2N',
                   'V+': 'VTK_VSP', 'V-': 'VTK_VSN', 'T1IN': 'VTK_TX', 'R1OUT': 'VTK_RX', 'T1OUT': 'VTK_TX_T', 'R1IN': 'VTK_RX_T',
                   'T2IN': 'GND', 'EN': 'GND', 'FORCEON': '+3V3', 'FORCEOFF': '+3V3'},
               nc=['T2OUT', 'R2IN', 'R2OUT', 'INVALID'])
    sh.text('EN = 0 — приёмники включены; FORCEON = FORCEOFF = VCC — автоотключение выключено.', (x - 30.48, y + 25.4))
    xc = x - 71.12
    C(sh, '100n', xc, y - 20.32, 'VTK_C1P', 'VTK_C1N')       # при VCC 3,0–3,6 В: C1 = C2 = C3 = 0,1 мкФ, C4 = 1 мкФ
    C(sh, '100n', xc, y - 10.16, 'VTK_C2P', 'VTK_C2N')
    C(sh, '100n', xc, y, 'VTK_VSP', 'GND')
    C(sh, '1u', xc, y + 10.16, 'VTK_VSN', 'GND')
    C(sh, '100n', xc, y + 20.32, '+3V3', 'GND')
    xa = 215.9
    j = sh.part('Connector_Generic:Conn_01x03', 'J', 'Vendotek RS-232: TXD / RXD / GND', (xa + 40.64, y), fp=TERM3,
                fields={'Примечание': 'TXD — выход платы (к RXD терминала), RXD — вход платы', 'Шелкография': 'TXD, RXD, GND'})
    sh.connect(j, {'1': 'VTK_TX_T', '2': 'VTK_RX_T', '3': 'GND'})
    return sh
