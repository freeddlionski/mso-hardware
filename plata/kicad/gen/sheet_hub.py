"""Лист «Табло и часы»: буферы HUB75 (2 × 74HCT245 от 5 В), разъём IDC-16, часы PCF8563 с батареей CR2032."""
from sheet_power import C, R, flag, two

# HUB75 (64×32, скан 1/16): 1 R1, 2 G1, 3 B1, 4 GND, 5 R2, 6 G2, 7 B2, 8 GND, 9 A, 10 B, 11 C, 12 D, 13 CLK, 14 LAT, 15 OE, 16 GND
HUB_PIN = {'R1': 1, 'G1': 2, 'B1': 3, 'R2': 5, 'G2': 6, 'B2': 7, 'A': 9, 'B': 10, 'C': 11, 'D': 12, 'CLK': 13, 'LAT': 14, 'OE': 15}
BUF = [['R1', 'G1', 'B1', 'R2', 'G2', 'B2', 'A', 'B'], ['C', 'D', 'CLK', 'LAT', 'OE']]


def build(proj):
    from kisch import Sheet
    sh = Sheet(proj, 'hub', 'Табло и часы', paper='A3')
    sh.text('HUB75: 74HCT245 от 5 В (вход понимает 3,3 В), направление A→B, всегда включены; на выходах 33 Ом.', (20.32, 25.4), 1.5)

    for i, sigs in enumerate(BUF):
        x, y = 101.6, 66.04 + 76.2 * i
        u = sh.part('74xx:74HC245', 'U', '74HCT245', (x, y), fp='Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm', mpn='74HCT245PW')
        m = {'A->B': '+5V', 'CE': 'GND', 'VCC': '+5V', 'GND': 'GND'}
        for k in range(8):
            if k < len(sigs):
                m['A%d' % k] = 'HUB_' + sigs[k]
                m['B%d' % k] = 'HUBB_' + sigs[k]
            else:
                m['A%d' % k] = 'GND'
        nc = ['B%d' % k for k in range(len(sigs), 8)]
        sh.connect(u, m, nc=nc)
        C(sh, '100n', x - 63.5, y - 15.24, '+5V', 'GND')
        if i == 1:
            R(sh, '10k', x - 63.5, y - 5.08, 'HUB_CLK', 'GND')   # GPIO3 — настроечный вывод: определённый уровень при сбросе
            R(sh, '10k', x - 63.5, y + 5.08, '+3V3', 'HUB_OE')   # Kimi K-006: до старта прошивки OE = 1 — табло погашено
        for k, s in enumerate(sigs):
            R(sh, '33', x + 50.8, y - 25.4 + 7.62 * k, 'HUBB_' + s, 'HUBO_' + s)

    j = sh.part('Connector_Generic:Conn_02x08_Odd_Even', 'J', 'HUB75 IDC-16', (218.44, 96.52),
                fp='Connector_IDC:IDC-Header_2x08_P2.54mm_Vertical', fields={'Примечание': 'с ключом; второе табло — цепочкой', 'Шелкография': 'HUB75'})
    m = {str(n): 'HUBO_' + s for s, n in HUB_PIN.items()}
    m.update({'4': 'GND', '8': 'GND', '16': 'GND'})
    sh.connect(j, m)

    # ---------- часы ----------
    x, y = 279.4, 205.74
    sh.text('Часы PCF8563 (I2C 47/48), кварц 32,768 кГц, CR2032; питание через BAT54C — от 3,3 В или батареи.', (190.5, 165.1), 1.5)
    u = sh.part('Timer_RTC:PCF8563T', 'U', 'PCF8563T', (x, y), mpn='PCF8563T/5')
    sh.connect(u, {'OSCI': 'RTC_XI', 'OSCO': 'RTC_XO', 'VSS': 'GND', 'SDA': 'RTC_SDA', 'SCL': 'RTC_SCL', 'VDD': 'VRTC'},
               nc=['~{INT}', 'CLKO'])
    y1 = sh.part('Device:Crystal', 'Y', '32.768kHz', (x - 50.8, y + 25.4), fp='Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm')
    sh.connect(y1, {'1': 'RTC_XI', '2': 'RTC_XO'})
    # у PCF8563 ёмкость на OSCO встроенная; на OSCI — только подстройка (не устанавливается), кварц CL 7–12,5 пФ
    C(sh, '10p DNP', x - 76.2, y + 38.1, 'RTC_XI', 'GND').dnp = True
    d = sh.part('Diode:BAT54C', 'D', 'BAT54C', (x - 50.8, y - 15.24), mpn='BAT54C')
    sh.connect(d, {'1': '+3V3', '2': 'VBAT', '3': 'VRTC'})
    C(sh, '100n', x - 50.8, y - 2.54, 'VRTC', 'GND')
    b = sh.part('Device:Battery_Cell', 'BT', 'CR2032', (x - 88.9, y - 12.7), fp='Battery:BatteryHolder_MYOUNG_BS-07-A1BJ001_CR2032')
    sh.connect(b, {'+': 'VBAT', '-': 'GND'})
    flag(sh, x - 25.4, y - 25.4, 'VRTC')
    R(sh, '4.7k', x + 40.64, y - 10.16, '+3V3', 'RTC_SDA')
    R(sh, '4.7k', x + 40.64, y, '+3V3', 'RTC_SCL')
    return sh
