"""Лист «Тестовые точки» (аудит Codex C-014, Kimi K-004; DESIGN §4 «Диагностика»).
Площадки Ø1,5 мм под щуп, в BOM не входят (не паяются). Ставятся при трассировке рядом со своими цепями."""

NETS = [
    ('VIN_F', 'вход после предохранителя'), ('+24V_P', 'после eFuse'), ('+12V', ''), ('+5V', ''), ('+3V3', ''),
    ('+5V_LCD1', 'табло 1'), ('+5V_LCD2', 'табло 2'), ('SW_VCORE', 'ядро коммутатора'),
    ('GND', ''), ('GND', ''), ('GND', ''),
    ('ESP_EN', 'сброс ESP32'), ('ESP_IO0', 'BOOT'), ('U0_TX', 'UART0'), ('U0_RX', 'UART0'),
    ('MDB_TX', ''), ('MDB_RX', ''), ('RS485_A', ''), ('RS485_B', ''), ('RTC_SCL', 'I2C'), ('RTC_SDA', 'I2C'),
]


def build(proj, known):
    from kisch import Sheet
    sh = Sheet(proj, 'tp', 'Тестовые точки', paper='A4')
    sh.text('Тестовые точки: площадки под щуп, не паяются (в BOM нет).', (20.32, 20.32), 1.5)
    n = 0
    for net, note in NETS:
        if net not in known:
            raise SystemExit('тестовая точка: нет цепи %s' % net)
        x, y = 40.64 + 50.8 * (n % 4), 45.72 + 20.32 * (n // 4)
        p = sh.part('Connector:TestPoint', 'TP', net + (' ' + note if note else ''), (x, y),
                    fp='TestPoint:TestPoint_Pad_D1.5mm', in_bom=False)
        sh.connect(p, {'1': net})
        n += 1
    return sh
