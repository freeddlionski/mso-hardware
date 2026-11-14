"""Лист «Ethernet»: W5500 + RJ45 HR911105A (трансформатор и светодиоды внутри).
Обвязка — по схеме платы той же серии с HR911105A (a147/Motherboard_Schematic.pdf, лист W5500) и даташиту W5500.
"""
from sheet_power import C, R, two


def build(proj):
    from kisch import Sheet
    sh = Sheet(proj, 'eth', 'Ethernet', paper='A3')

    x, y = 165.1, 109.22
    u = sh.part('Interface_Ethernet:W5500', 'U', 'W5500', (x, y), lcsc='C32843', mpn='W5500')
    sh.connect(u, {
        'AVDD': '+3V3A', 'AGND': 'GND', 'VDD': '+3V3', 'GND': 'GND',
        'EXRES1': 'ETH_EXRES', 'TOCAP': 'ETH_TOCAP', '1V2O': 'ETH_1V2',
        '23': 'GND',                        # RSVD 23 — на землю; 38–42 — NC (даташит W5500 с v1.0.2, внутренняя подтяжка к земле)
        'PMODE0': '+3V3', 'PMODE1': '+3V3', 'PMODE2': '+3V3',   # 111 — все режимы, автосогласование
        'XI/CLKIN': 'ETH_XI', 'XO': 'ETH_XO',
        '~{SCS}': 'ETH_CS', 'SCLK': 'ETH_SCLK', 'MISO': 'ETH_MISO', 'MOSI': 'ETH_MOSI', '~{INT}': 'ETH_INT', '~{RST}': 'ESP_EN',
        'TXP': 'ETH_TXP', 'TXN': 'ETH_TXN', 'RXP': 'ETH_RXP', 'RXN': 'ETH_RXN',
        'LINKLED': 'ETH_LINKLED', 'ACTLED': 'ETH_ACTLED',
    }, nc=['DNC', 'NC', 'VBG', 'SPDLED', 'DUPLED', '38', '39', '40', '41', '42'])
    sh.text('W5500: AVDD через ферритовую бусину (+3V3A), EXRES1 12,4 кОм 1 %. PMODE = 111 — автосогласование.', (x - 50.8, y - 60.96))

    # питание
    xl = 40.64
    two(sh, 'Device:FerriteBead', 'FB', '600R@100MHz', xl, 38.1, '+3V3', '+3V3A', fp='Inductor_SMD:L_0805_2012Metric')
    from sheet_power import flag
    flag(sh, xl + 40.64, 38.1, '+3V3A')
    C(sh, '10u', xl, 48.26, '+3V3A', 'GND', 'C0805')
    for i in range(3):
        C(sh, '100n', xl, 58.42 + 10.16 * i, '+3V3A', 'GND')
    C(sh, '100n', xl, 88.9, '+3V3', 'GND')
    C(sh, '10u', xl, 99.06, '+3V3', 'GND', 'C0805')
    R(sh, '12.4k 1%', xl, 116.84, 'ETH_EXRES', 'GND')
    C(sh, '4.7u', xl, 127.0, 'ETH_TOCAP', 'GND', 'C0805')
    C(sh, '10n', xl, 137.16, 'ETH_1V2', 'GND')
    sh.text('Сброс W5500 — от EN модуля ESP32 (общий сброс, RC 10 кОм / 1 мкФ на листе MCU)', (xl - 10.16, 157.48))

    # кварц 25 МГц
    q = sh.part('Device:Crystal_GND24', 'Y', '25MHz 20ppm', (xl + 5.08, 190.5), fp='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm')
    sh.connect(q, {'1': 'ETH_XI', '3': 'ETH_XO', 'G': 'GND'})
    C(sh, '18p', xl - 22.86, 210.82, 'ETH_XI', 'GND')
    C(sh, '18p', xl + 22.86, 210.82, 'ETH_XO', 'GND')
    R(sh, '1M', xl, 177.8, 'ETH_XI', 'ETH_XO')

    # линия к RJ45
    xr = 281.94
    sh.text('Передача: 49,9 Ом на +3V3A, средняя точка через 10 Ом + 22 нФ. Приём: 6,8 нФ последовательно, 2 × 82 Ом + 10 нФ.',
            (xr - 50.8, 30.48))
    R(sh, '49.9 1%', xr - 25.4, 40.64, 'ETH_TXP', '+3V3A')
    R(sh, '49.9 1%', xr - 25.4, 50.8, 'ETH_TXN', '+3V3A')
    R(sh, '10', xr - 25.4, 60.96, '+3V3A', 'ETH_TCT')
    C(sh, '22n', xr - 25.4, 71.12, 'ETH_TCT', 'GND')
    C(sh, '6.8n', xr - 25.4, 86.36, 'ETH_RXP', 'ETH_RDP')
    C(sh, '6.8n', xr - 25.4, 96.52, 'ETH_RXN', 'ETH_RDN')
    R(sh, '82', xr - 25.4, 106.68, 'ETH_RDP', 'ETH_RCT')
    R(sh, '82', xr - 25.4, 116.84, 'ETH_RCT', 'ETH_RDN')
    C(sh, '10n', xr - 25.4, 127.0, 'ETH_RCT', 'GND')
    R(sh, '82', xr - 25.4, 142.24, 'ETH_LED_Y', 'ETH_LINKLED')
    R(sh, '82', xr - 25.4, 152.4, 'ETH_LED_G', 'ETH_ACTLED')

    j = sh.part('Connector:RJ45_Hanrun_HR911105A_Horizontal', 'J', 'RJ45 HR911105A', (xr + 40.64, 101.6), mpn='HR911105A')
    # 9/12 — аноды светодиодов, 10/11 — катоды; 8 — корпус (как на плате той же серии, лист W5500)
    sh.connect(j, {'1': 'ETH_TXP', '2': 'ETH_TXN', '3': 'ETH_RDP', '6': 'ETH_RDN', '4': 'ETH_TCT', '5': 'ETH_RCT',
                   '12': '+3V3A', '9': '+3V3A', '11': 'ETH_LED_Y', '10': 'ETH_LED_G', '8': 'GND', 'SH': 'GND'}, nc=['7'])
    return sh
