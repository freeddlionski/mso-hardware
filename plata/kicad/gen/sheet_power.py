"""Лист «Питание»: вход 24 В, защита, выходы Vendotek и MDB, преобразователи 12 / 5 / 3,3 В и два канала табло.
Расчёты и выбор — plata/DESIGN.md, раздел 2.
"""

FP = {
    'R0603': 'Resistor_SMD:R_0603_1608Metric',
    'R0805': 'Resistor_SMD:R_0805_2012Metric',
    'C0603': 'Capacitor_SMD:C_0603_1608Metric',
    'C0805': 'Capacitor_SMD:C_0805_2012Metric',
    'C1206': 'Capacitor_SMD:C_1206_3216Metric',
    'C1210': 'Capacitor_SMD:C_1210_3225Metric',
    'LED0603': 'LED_SMD:LED_0603_1608Metric',
    'PTC1812': 'Fuse:Fuse_1812_4532Metric',
    'PTC2920': 'Fuse:Fuse_2920_7451Metric',
    'TERM2_508': 'Connector_Phoenix_MSTB:PhoenixContact_MSTBA_2,5_2-G-5,08_1x02_P5.08mm_Horizontal',
}


def two(sh, lib, prefix, value, x, y, n1, n2, fp='', lcsc='', mpn='', **kw):
    """Двухвыводная деталь горизонтально: вывод 1 слева, 2 справа."""
    p = sh.part(lib, prefix, value, (x, y), rot=90, fp=fp, lcsc=lcsc, mpn=mpn, **kw)
    sh.connect(p, {'1': n1, '2': n2})
    return p


def R(sh, v, x, y, a, b, fp='R0603'):
    return two(sh, 'Device:R', 'R', v, x, y, a, b, FP[fp])


def C(sh, v, x, y, a, b, fp='C0603'):
    return two(sh, 'Device:C', 'C', v, x, y, a, b, FP[fp])


def led(sh, x, y, net, color='зелёный', r='2.2k'):
    """Индикатор линии: net → R → LED → GND."""
    mid = 'LED_' + net.strip('+')
    R(sh, r, x, y, net, mid)
    p = sh.part('Device:LED', 'D', color, (x + 43.18, y), rot=180, fp=FP['LED0603'])
    sh.connect(p, {'A': mid, 'K': 'GND'})


def flag(sh, x, y, net):
    p = sh.part('power:PWR_FLAG', '#FLG', 'PWR_FLAG', (x, y), ref=sh.proj.next_ref('#FLG0'))
    sh.connect(p, {'1': net})


def lmr51430(sh, x, y, tag, vout, rfbb, l, cout_fp, out):
    """24 В → vout. LMR51430XDDCR, 500 кГц. VOUT = 0,6 × (1 + 100k / RFBB)."""
    sw, fb, cb, en = tag + '_SW', tag + '_FB', tag + '_CB', tag + '_EN'
    u = sh.part('Regulator_Switching:LMR51430', 'U', 'LMR51430XDDCR', (x, y),
                fp='Package_TO_SOT_SMD:SOT-23-6', lcsc='C5185863', mpn='LMR51430XDDCR')
    sh.connect(u, {'VIN': '+24V_P', 'EN': en, 'GND': 'GND', 'CB': cb, 'SW': sw, 'FB': fb})
    sh.text('%s: 24 В → %s, LMR51430 500 кГц' % (tag, vout), (x - 40.64, y - 12.7))
    C(sh, '10u 50V', x - 40.64, y - 5.08, '+24V_P', 'GND', 'C1210')
    C(sh, '100n 50V', x - 40.64, y + 2.54, '+24V_P', 'GND')
    R(sh, '100k', x - 40.64, y + 10.16, '+24V_P', en)          # EN: порог ~1,2 В → включение от ~15 В
    R(sh, '8.66k', x - 40.64, y + 17.78, en, 'GND')
    C(sh, '100n', x + 35.56, y - 10.16, cb, sw)
    two(sh, 'Device:L', 'L', l, x + 35.56, y - 2.54, sw, out, fp='Inductor_SMD:L_Taiyo-Yuden_NR-50xx')
    R(sh, '100k', x + 35.56, y + 5.08, out, fb)
    R(sh, rfbb, x + 35.56, y + 12.7, fb, 'GND')
    C(sh, '22u', x + 76.2, y - 2.54, out, 'GND', cout_fp)
    C(sh, '22u', x + 76.2, y + 5.08, out, 'GND', cout_fp)
    C(sh, '100n', x + 76.2, y + 12.7, out, 'GND')
    flag(sh, x + 106.68, y - 2.54, out)
    led(sh, x + 106.68, y + 7.62, out)


def lm61460(sh, x, y, tag, out, term_ref_note):
    """24 В → 5 В / 5 А на табло. LM61460AANRJRR, 400 кГц (RT 33,2 кОм). VOUT = 1,0 × (1 + 100k / 24,9k) = 5,02 В."""
    sw, fb, cb, rb, en, vcc, rt, raw = (tag + s for s in ('_SW', '_FB', '_CB', '_RB', '_EN', '_VCC', '_RT', '_RAW'))
    u = sh.part('mso74:LM61460', 'U', 'LM61460AANRJRR', (x, y), fp='mso74:Texas_RJR_VQFN-HR-14_3.5x4mm',
                lcsc='C2864505', mpn='LM61460AANRJRR')
    sh.connect(u, {'VIN1': '+24V_P', 'VIN2': '+24V_P', 'EN/SYNC': en, 'RT': rt, 'BIAS': raw, 'VCC': vcc,
                   'CBOOT': cb, 'RBOOT': rb, 'SW': sw, 'FB': fb, 'AGND': 'GND', 'PGND1': 'GND', 'PGND2': 'GND'},
               nc=['PGOOD'])
    sh.text('%s: 24 В → 5 В / 5 А, LM61460 400 кГц — %s' % (tag, term_ref_note), (x - 43.18, y - 15.24))
    C(sh, '10u 50V', x - 43.18, y - 7.62, '+24V_P', 'GND', 'C1210')
    C(sh, '10u 50V', x - 43.18, y, '+24V_P', 'GND', 'C1210')
    C(sh, '100n 50V', x - 43.18, y + 7.62, '+24V_P', 'GND')      # у VIN1
    C(sh, '100n 50V', x - 43.18, y + 15.24, '+24V_P', 'GND')     # у VIN2
    R(sh, '100k', x - 43.18, y + 22.86, '+24V_P', en)           # EN ~1,26 В → включение от ~14 В
    R(sh, '10k', x - 43.18, y + 30.48, en, 'GND')
    R(sh, '33.2k 1%', x - 43.18, y + 38.1, rt, 'GND')
    C(sh, '1u', x - 43.18, y + 45.72, vcc, 'GND')
    C(sh, '100n', x + 38.1, y - 12.7, cb, sw)
    R(sh, '0', x + 38.1, y - 5.08, rb, cb)                      # RBOOT: скорость фронта SW, 0 Ом — быстро
    two(sh, 'Device:L', 'L', '6.8u 8A', x + 38.1, y + 2.54, sw, raw, fp='Inductor_SMD:L_12x12mm_H6mm')
    R(sh, '100k 1%', x + 38.1, y + 10.16, raw, fb)
    R(sh, '24.9k 1%', x + 38.1, y + 17.78, fb, 'GND')
    for i in range(4):
        C(sh, '47u 10V', x + 78.74, y - 7.62 + 7.62 * i, raw, 'GND', 'C1210')
    two(sh, 'Device:Polyfuse', 'F', '5A удерж.', x + 78.74, y + 25.4, raw, out, fp=FP['PTC2920'])
    p = sh.part('Device:C_Polarized', 'C', '470u 10V', (x + 109.22, y + 22.86), fp='Capacitor_SMD:CP_Elec_10x10.5')
    sh.connect(p, {'1': out, '2': 'GND'})
    flag(sh, x + 109.22, y + 35.56, out)
    flag(sh, x + 109.22, y + 45.72, raw)   # BIAS питается от выхода до предохранителя
    led(sh, x + 78.74, y + 40.64, out, r='1k')
    j = sh.part('Connector_Generic:Conn_01x02', 'J', 'Табло ' + tag[-1] + ': +5V / GND', (x + 124.46, y + 2.54),
                fp=FP['TERM2_508'], fields={'Примечание': 'разъёмный 5,08, другой цвет, чем +24 В'})
    sh.connect(j, {'1': out, '2': 'GND'})


def build(proj):
    from kisch import Sheet
    sh = Sheet(proj, 'power', 'Питание', paper='A2')

    # ---- вход 24 В ----
    x, y = 30.48, 38.1
    sh.text('ВХОД 18–32 В (номинал 24 В). Переполюсовка: Q1 закрыт, плата не включается, предохранитель цел.', (x - 10.16, y - 17.78), 1.5)
    j = sh.part('Connector_Generic:Conn_01x02', 'J', 'Питание +24V / GND', (x, y), fp=FP['TERM2_508'],
                fields={'Примечание': 'отдельно от сигнальных клемм'})
    sh.connect(j, {'1': 'VIN_RAW', '2': 'GND'})
    two(sh, 'Device:Fuse', 'F', '7.5A', x + 30.48, y, 'VIN_RAW', 'VIN_F',
        fp='Fuse:Fuseholder_Blade_Mini_Keystone_3568', fields={'Примечание': 'держатель mini-blade, вставка 7,5 А'})
    two(sh, 'Device:D_TVS', 'D', 'SMCJ33CA', x + 30.48, y + 12.7, 'VIN_F', 'GND', fp='Diode_SMD:D_SMC', mpn='SMCJ33CA')
    q = sh.part('Transistor_FET:SUD50P06-15', 'Q', 'SUD50P06-15', (x + 76.2, y + 2.54), mpn='SUD50P06-15')
    sh.connect(q, {'D': 'VIN_F', 'S': '+24V_P', 'G': 'Q_IN_G'})
    two(sh, 'Device:D_Zener', 'D', '15V', x + 109.22, y + 15.24, '+24V_P', 'Q_IN_G', fp='Diode_SMD:D_SOD-123', mpn='MMSZ5245B')
    R(sh, '47k', x + 109.22, y + 22.86, 'Q_IN_G', 'GND')
    flag(sh, x + 139.7, y - 5.08, '+24V_P')
    flag(sh, x - 15.24, y + 25.4, 'GND')
    led(sh, x + 139.7, y + 5.08, '+24V_P', r='22k')

    # ---- выходы 24 В: Vendotek и MDB ----
    x, y = 30.48, 99.06
    sh.text('ПИТАНИЕ ТЕРМИНАЛА VENDOTEK (12–48 В, переполюсовка его убивает): после Q1, разъём с ключом, подписи «+24 V» / «GND».',
            (x - 10.16, y - 12.7), 1.5)
    two(sh, 'Device:Polyfuse', 'F', '1.1A удерж.', x + 30.48, y, '+24V_P', 'VTK_24V', fp=FP['PTC1812'])
    j = sh.part('Connector_Generic:Conn_01x02', 'J', 'Vendotek: +24V / GND', (x + 76.2, y + 2.54), fp=FP['TERM2_508'],
                fields={'Примечание': 'разъёмный с ключом, крупные подписи + и GND'})
    sh.connect(j, {'1': 'VTK_24V', '2': 'GND'})
    led(sh, x + 101.6, y, 'VTK_24V', r='22k')
    two(sh, 'Device:Polyfuse', 'F', '1.5A удерж.', x + 30.48, y + 22.86, '+24V_P', 'MDB_24V', fp=FP['PTC1812'])
    sh.text('MDB_24V → конт. 1 разъёма MDB (лист «MDB и входы»)', (x + 50.8, y + 17.78))
    led(sh, x + 101.6, y + 22.86, 'MDB_24V', r='22k')

    # ---- преобразователи 12 / 5 / 3,3 В ----
    lmr51430(sh, 71.12, 165.1, 'P12', '+12V', '5.23k 1%', '15u', 'C1210', '+12V')
    lmr51430(sh, 71.12, 215.9, 'P5', '+5V', '13.7k 1%', '10u', 'C1206', '+5V')
    lmr51430(sh, 71.12, 266.7, 'P3', '+3V3', '22.1k 1%', '6.8u', 'C1206', '+3V3')

    # ---- два канала табло ----
    lm61460(sh, 304.8, 63.5, 'LCD1', '+5V_LCD1', 'табло 1')
    lm61460(sh, 304.8, 180.34, 'LCD2', '+5V_LCD2', 'табло 2')
    return sh
