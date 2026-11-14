"""Лист «Ethernet»: W5500 + встроенный коммутатор RTL8305NB, два RJ45 HR911105A (сеть и Vendotek).
W5500 — по схеме платы той же серии (a147/Motherboard_Schematic.pdf, лист W5500) и даташиту W5500.
Коммутатор (Павел 14.11: «Давай 2 rj45… При штатной работе будет выглядеть компактно и никакого колхоза»):
обвязка RTL8305NB-VB-CG — по открытой проверенной схеме свитча на этом чипе (EasyEDA, MAIN_VT1.0, 2022-08-13,
прислал Павел) и даташиту Realtek. Порт 0 — к W5500 через трансформатор H1102 (как кабель нулевой длины),
порт 1 — RJ45 «Сеть», порт 2 — RJ45 «Vendotek», порты 3–4 не используются. Прошивка не меняется.
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
        'ACTLED': 'ETH_ACTLED',
    }, nc=['DNC', 'NC', 'VBG', 'SPDLED', 'DUPLED', 'LINKLED', '38', '39', '40', '41', '42'])
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
    R(sh, '82', xr - 25.4, 152.4, 'ETH_LED_G', 'ETH_ACTLED')

    # ---- W5500 ↔ коммутатор: трансформатор H1102 (сторона W5500 — со своей обвязкой выше, сторона RTL — CT на 100 нФ)
    t = sh.part('Transformer:Wuerth_749013011A', 'T', 'H1102N', (xr + 30.48, 101.6),
                fp='Transformer_SMD:Transformer_Ethernet_CNDtek_H1102N', mpn='CND-tek H1102N')
    sh.connect(t, {'1': 'ETH_TXP', '3': 'ETH_TXN', '2': 'ETH_TCT', '6': 'ETH_RDP', '8': 'ETH_RDN', '7': 'ETH_RCT',
                   '16': 'SW_RXP0', '14': 'SW_RXN0', '15': 'SW_CT0A', '11': 'SW_TXP0', '9': 'SW_TXN0', '10': 'SW_CT0B'})
    C(sh, '100n', xr + 30.48, 132.08, 'SW_CT0A', 'GND')
    C(sh, '100n', xr + 30.48, 142.24, 'SW_CT0B', 'GND')
    sh.text('W5500 ↔ порт 0 RTL8305NB через H1102 — как короткий кабель. Светодиод «активность» на RJ45 «Сеть» — от W5500.',
            (xr - 50.8, 167.64))
    rj45(sh, 1, 'RJ45 Сеть', xr + 81.28, 101.6)
    return sh


def switch(proj):
    from kisch import Sheet
    sh = Sheet(proj, 'sw', 'Коммутатор Ethernet', paper='A3')
    x, y = 165.1, 132.08
    u = sh.part('mso74:RTL8305NB', 'U', 'RTL8305NB-VB-CG', (x, y), mpn='RTL8305NB-VB-CG')
    m = {'44': 'SW_RXP0', '45': 'SW_RXN0', '46': 'SW_TXN0', '47': 'SW_TXP0',
         '2': 'SW_RXP1', '3': 'SW_RXN1', '4': 'SW_TXN1', '5': 'SW_TXP1',
         '12': 'SW_RXP2', '11': 'SW_RXN2', '10': 'SW_TXN2', '9': 'SW_TXP2',
         '40': 'SW_XI', '39': 'SW_XO', '42': 'SW_IBREF', '27': 'SW_RST',
         '37': '+3V3', '6': '+3V3', '8': '+3V3', '18': '+3V3', '48': '+3V3', '38': '+3V3', '31': '+3V3',
         '36': 'SW_1V0', '1': 'SW_1V0', '13': 'SW_1V0', '23': 'SW_1V0', '43': 'SW_1V0', '41': 'SW_1V0',
         '7': 'SW_1V0', '24': 'SW_1V0', '35': 'SW_1V0',
         '30': 'SW_LED1', '32': 'SW_LED2', '49': 'GND'}
    sh.connect(u, m, nc=['14', '15', '16', '17', '19', '20', '21', '22', '29', '33', '34', '28', '25', '26'])
    sh.text('RTL8305NB: питание 3,3 В напрямую (как в образце); 1,0 В — встроенный стабилизатор V12OUT, только для себя '
            '(даташит: не питать другие микросхемы, без бусины между V12OUT и AVDDLPLL). Режимы — по умолчанию, без EEPROM.',
            (x - 76.2, y - 81.28), 1.27)
    # питание
    xl = 40.64
    p = sh.part('Device:C_Polarized', 'C', '220u 10V', (xl, 45.72), rot=90, fp='Capacitor_SMD:CP_Elec_6.3x5.4')
    sh.connect(p, {'1': 'SW_1V0', '2': 'GND'})
    C(sh, '1u', xl, 55.88, 'SW_1V0', 'GND')
    for i in range(9):
        C(sh, '100n', xl, 66.04 + 10.16 * i, 'SW_1V0', 'GND')
    C(sh, '10u', xl + 50.8, 45.72, '+3V3', 'GND', 'C0805')
    C(sh, '1u', xl + 50.8, 55.88, '+3V3', 'GND')
    for i in range(7):
        C(sh, '100n', xl + 50.8, 66.04 + 10.16 * i, '+3V3', 'GND')
    # опорный резистор, сброс, кварц
    R(sh, '2.49k 1%', xl, 172.72, 'SW_IBREF', 'GND')
    R(sh, '10k', xl, 187.96, '+3V3', 'SW_RST')
    C(sh, '1u', xl, 198.12, 'SW_RST', 'GND')
    sh.text('Сброс RC 10 кОм / 1 мкФ ≈ 10 мс (даташит: Td > 5 мс). IBREF 2,49 кОм 1 %.', (xl - 10.16, 210.82))
    q = sh.part('Device:Crystal_GND24', 'Y', '25MHz 20ppm', (xl + 5.08, 238.76), fp='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm')
    sh.connect(q, {'1': 'SW_XI', '3': 'SW_XO', 'G': 'GND'})
    C(sh, '18p', xl - 22.86, 254.0, 'SW_XI', 'GND')
    C(sh, '18p', xl + 22.86, 254.0, 'SW_XO', 'GND')

    rj45(sh, 2, 'RJ45 Vendotek', 304.8, 180.34)
    return sh



def rj45(sh, port, name, xr, yy):
    """RJ45 HR911105A на порт коммутатора. Как в образце: TX− 6, TX+ 3, RX− 2, RX+ 1, средние точки 4 и 5 вместе на
    100 нФ к земле; жёлтый светодиод — PxLED → 330 Ом → 12, 11 — земля. Зелёный у «Сети» — активность W5500."""
    j = sh.part('Connector:RJ45_Hanrun_HR911105A_Horizontal', 'J', name, (xr, yy), mpn='HR911105A',
                fields={'Шелкография': 'LAN' if port == 1 else 'VENDOTEK'})
    pins = {'1': 'SW_RXP%d' % port, '2': 'SW_RXN%d' % port, '3': 'SW_TXP%d' % port, '6': 'SW_TXN%d' % port,
            '4': 'SW_CT%d' % port, '5': 'SW_CT%d' % port, '12': 'SW_LEDA%d' % port, '11': 'GND', '8': 'GND', 'SH': 'GND'}
    nc = ['7']
    if port == 1:
        pins.update({'9': '+3V3A', '10': 'ETH_LED_G'})
    else:
        nc += ['9', '10']
    sh.connect(j, pins, nc=nc)
    C(sh, '100n', xr - 50.8, yy + 15.24, 'SW_CT%d' % port, 'GND')
    R(sh, '330', xr - 50.8, yy + 25.4, 'SW_LED%d' % port, 'SW_LEDA%d' % port)
