"""Лист «Расширитель»: PCA9555 на шине I2C часов (GPIO 47/48), адрес 0x20 — 4 входа и 4 выхода на клеммы,
8 линий — на гребёнку (не устанавливается). Решение Павла 14.11: «4 входа и выхода — более чем большой запас».

Входы — сухой контакт / открытый коллектор на минус (как сервисная кнопка): клемма → самовосст. 50 мА → TVS 5 В → 1 кОм → вход,
подтяжка 10 кОм к 3,3 В. Выходы — ключ на минус DMN6140L (60 В): до 0,5 А, TVS 33 В на стоке от индуктивной нагрузки,
самовосст. 0,75 А. Прерывание PCA9555 не подключено (нет свободного вывода) — прошивка опрашивает раз в 10–20 мс.
"""
from sheet_io import TERM, blocked_input
from sheet_power import C, R, tvs, two

IN = ['EXT_IN1', 'EXT_IN2', 'EXT_IN3', 'EXT_IN4']
OUT = ['EXT_OUT1', 'EXT_OUT2', 'EXT_OUT3', 'EXT_OUT4']


def build(proj):
    from kisch import Sheet
    sh = Sheet(proj, 'ext', 'Расширитель входов-выходов', paper='A3')
    sh.text('PCA9555 (I2C 0x20) на шине часов. Входы — сухой контакт на минус; выходы — ключ на минус до 0,5 А, 24 В.', (20.32, 25.4), 1.5)

    x, y = 165.1, 109.22
    u = sh.part('Interface_Expansion:PCA9555PW', 'U', 'PCA9555PW', (x, y), mpn='PCA9555PW')
    m = {'VDD': '+3V3', 'VSS': 'GND', 'A0': 'GND', 'A1': 'GND', 'A2': 'GND', 'SCL': 'RTC_SCL', 'SDA': 'RTC_SDA'}
    for i in range(4):
        m['IO0_%d' % i] = 'EXT_I%d' % (i + 1)
        m['IO0_%d' % (i + 4)] = 'EXT_G%d' % (i + 1)
    for i in range(8):
        m['IO1_%d' % i] = 'EXT_P%d' % i
    sh.connect(u, m, nc=['~{INT}'])
    C(sh, '100n', x - 50.8, y - 30.48, '+3V3', 'GND')

    # входы
    for i in range(4):   # доп. замечание аудитора: без блокирующего диода +24 В питало бы 3,3 В через диоды PCA9555
        blocked_input(sh, 50.8, 45.72 + 25.4 * i, IN[i], 'EXT_I%d' % (i + 1), 'EXTI%d' % (i + 1))

    # выходы
    # аудит 2, п. 13: RDS(on) DMN6140L нормирован при VGS 4,5 В → затворы от буфера 74AHCT125 (питание 5 В, вход понимает 3,3 В)
    bref = proj.next_ref('U')
    gates = [('2', '1', '3'), ('5', '4', '6'), ('9', '10', '8'), ('12', '13', '11')]   # A, OE, Y
    for i, (a, oe, yq) in enumerate(gates):
        b = sh.part('74xx:74AHCT125', 'U', '74AHCT125', (190.5, 165.1 + 25.4 * i), unit=i + 1, ref=bref,
                    fp='Package_SO:TSSOP-14_4.4x5mm_P0.65mm', mpn='74AHCT125PW')
        sh.connect(b, {a: 'EXT_G%d' % (i + 1), oe: 'GND', yq: 'EXT_GB%d' % (i + 1)})
        R(sh, '100k', 157.48, 172.72 + 25.4 * i, 'EXT_G%d' % (i + 1), 'GND')    # при сбросе выводы PCA9555 — входы: ключ закрыт
    b = sh.part('74xx:74AHCT125', 'U', '74AHCT125', (190.5, 271.78), unit=5, ref=bref,
                fp='Package_SO:TSSOP-14_4.4x5mm_P0.65mm', mpn='74AHCT125PW')
    sh.connect(b, {'VCC': '+5V', 'GND': 'GND'})
    C(sh, '100n', 157.48, 271.78, '+5V', 'GND')
    for i in range(4):
        yy = 165.1 + 25.4 * i
        R(sh, '100', 228.6, yy, 'EXT_GB%d' % (i + 1), 'EXT_GG%d' % (i + 1))
        R(sh, '100k', 228.6, yy + 10.16, 'EXT_GG%d' % (i + 1), 'GND')
        q = sh.part('Transistor_FET:DMN6140L', 'Q', 'DMN6140L', (264.16, yy + 2.54), mpn='DMN6140L-7')
        sh.connect(q, {'G': 'EXT_GG%d' % (i + 1), 'S': 'GND', 'D': 'EXT_D%d' % (i + 1)})
        tvs(sh, 'SMAJ33A', 299.72, yy + 10.16, 'EXT_D%d' % (i + 1))     # аудит 2, п. 4: катод к стоку (было наоборот)
        two(sh, 'Device:Polyfuse', 'F', '0.75A удерж.', 299.72, yy, 'EXT_D%d' % (i + 1), OUT[i], fp='Fuse:Fuse_2920_7451Metric')

    two(sh, 'Device:Polyfuse', 'F', '1.1A удерж.', 299.72, 147.32, '+24V_P', 'EXT_24V', fp='Fuse:Fuse_2920_7451Metric')

    # клеммы
    j = sh.part('Connector_Generic:Conn_01x06', 'J', 'Входы: ВХ1–ВХ4 / GND / GND', (25.4, 165.1), fp=TERM[6],
                 fields={'Шелкография': 'IN1, IN2, IN3, IN4, GND, GND'})
    sh.connect(j, {'1': IN[0], '2': IN[1], '3': IN[2], '4': IN[3], '5': 'GND', '6': 'GND'})
    j = sh.part('Connector_Generic:Conn_01x06', 'J', 'Выходы: +24V / ВЫХ1–ВЫХ4 / GND', (370.84, 190.5), fp=TERM[6],
                 fields={'Шелкография': '+24V, OUT1, OUT2, OUT3, OUT4, GND'})
    sh.connect(j, {'1': 'EXT_24V', '2': OUT[0], '3': OUT[1], '4': OUT[2], '5': OUT[3], '6': 'GND'})
    j = sh.part('Connector_Generic:Conn_02x05_Odd_Even', 'J', 'Резерв PCA9555 P1.0–P1.7', (370.84, 101.6),
                fp='Connector_PinHeader_2.54mm:PinHeader_2x05_P2.54mm_Vertical', dnp=True)
    mm = {str(k + 1): 'EXT_P%d' % k for k in range(8)}
    mm.update({'9': '+3V3', '10': 'GND'})
    sh.connect(j, mm)
    return sh
