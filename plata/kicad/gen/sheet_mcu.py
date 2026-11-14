"""Лист «ESP32-S3 и USB»: модуль WROOM-1U-N16R2, сброс и BOOT, автосброс, CH340K от 3,3 В, USB-C с защитой.
Назначение выводов — plata/PINOUT.md (главная таблица). Имена цепей ниже — те же, что на листах узлов.
"""
from sheet_power import C, R, FP, two

# GPIO → цепь (plata/PINOUT.md). IO19/IO20 в символе называются USB_D-/USB_D+.
GPIO = {
    'IO1': 'HUB_LAT', 'IO2': 'HUB_OE', 'IO3': 'HUB_CLK', 'IO4': 'HUB_C', 'IO5': 'HUB_A', 'IO6': 'HUB_B2',
    'IO7': 'VTK_TX', 'IO8': 'BILL_PULSE', 'IO9': 'COIN_PULSE',
    'IO10': 'ETH_CS', 'IO11': 'ETH_MOSI', 'IO12': 'ETH_SCLK', 'IO13': 'ETH_MISO', 'IO14': 'ETH_INT', 'IO15': 'VTK_RX',
    'IO16': 'HUB_R2', 'IO17': 'HUB_B1', 'IO18': 'HUB_R1', 'USB_D-': 'HUB_D', 'USB_D+': 'SERVICE_BTN', 'IO21': 'HUB_B',
    'IO35': 'MDB_RX', 'IO36': 'COIN_INH', 'IO37': 'MDB_TX', 'IO38': 'RS485_DE', 'IO39': 'RS485_TX', 'IO40': 'RS485_RX',
    'IO41': 'HUB_G2', 'IO42': 'HUB_G1', 'TXD0': 'U0_TX', 'RXD0': 'U0_RX', 'IO47': 'RTC_SCL', 'IO48': 'RTC_SDA',
}
# У модуля WROOM-1U нет выводов GPIO 33/34 (Vendotek на A147) — решение Павла 14.11 «своя плата — своя прошивка»:
# Vendotek на GPIO 7 (TX) и 15 (RX), сброс W5500 — от EN модуля (общий сброс).


def build(proj):
    from kisch import Sheet
    sh = Sheet(proj, 'mcu', 'ESP32-S3 и USB', paper='A3')

    u = sh.part('RF_Module:ESP32-S3-WROOM-1', 'U', 'ESP32-S3-WROOM-1U-N16R2', (165.1, 121.92),
                fp='RF_Module:ESP32-S3-WROOM-1U', lcsc='C3013945', mpn='ESP32-S3-WROOM-1U-N16R2')
    m = dict(GPIO)
    m.update({'3V3': '+3V3', 'GND': 'GND', 'EN': 'ESP_EN', 'IO0': 'ESP_IO0'})
    sh.connect(u, m, nc=['IO45', 'IO46'])
    sh.text('IO45, IO46 — выводы настройки загрузки, не подключать. Антенна — U.FL модуля → кабель на SMA в стенке корпуса.',
            (110.49, 68.58))

    # питание модуля
    x = 40.64
    sh.text('Развязка 3,3 В у модуля', (x - 10.16, 30.48))
    C(sh, '22u', x, 40.64, '+3V3', 'GND', 'C1206')
    C(sh, '10u', x, 50.8, '+3V3', 'GND', 'C0805')
    C(sh, '100n', x, 60.96, '+3V3', 'GND')
    C(sh, '100n', x, 71.12, '+3V3', 'GND')

    # сброс и BOOT
    sh.text('EN: RC 10 кОм / 1 мкФ, кнопка RESET. IO0: подтяжка, кнопка BOOT.', (x - 10.16, 88.9))
    R(sh, '10k', x, 99.06, '+3V3', 'ESP_EN')
    C(sh, '1u', x, 109.22, 'ESP_EN', 'GND')
    two(sh, 'Switch:SW_Push', 'SW', 'RESET', x, 119.38, 'ESP_EN', 'GND', fp='Button_Switch_SMD:SW_SPST_TL3342')
    R(sh, '10k', x, 132.08, '+3V3', 'ESP_IO0')
    two(sh, 'Switch:SW_Push', 'SW', 'BOOT', x, 142.24, 'ESP_IO0', 'GND', fp='Button_Switch_SMD:SW_SPST_TL3342')

    # автосброс (как на A147): DTR/RTS CH340K → EN/IO0
    x, y = 45.72, 172.72
    sh.text('Автосброс для прошивки (как на A147): DTR=0,RTS=1 → EN=0; DTR=1,RTS=0 → IO0=0.', (x - 15.24, y - 10.16))
    R(sh, '10k', x, y, 'USB_DTR', 'Q_AR1_B')
    q = sh.part('Transistor_BJT:MMBT3904', 'Q', 'MMBT3904', (x + 33.02, y), mpn='MMBT3904')
    sh.connect(q, {'B': 'Q_AR1_B', 'E': 'USB_RTS', 'C': 'ESP_EN'})
    R(sh, '10k', x, y + 20.32, 'USB_RTS', 'Q_AR2_B')
    q = sh.part('Transistor_BJT:MMBT3904', 'Q', 'MMBT3904', (x + 33.02, y + 20.32), mpn='MMBT3904')
    sh.connect(q, {'B': 'Q_AR2_B', 'E': 'USB_DTR', 'C': 'ESP_IO0'})

    # CH340K от 3,3 В (V3 = VCC — режим 3,3 В)
    x, y = 289.56, 76.2
    sh.text('CH340K от +3,3 В: уровни TXD/RXD = 3,3 В (на A147 был 5 В на входе ESP32).', (x - 30.48, y - 22.86))
    ch = sh.part('Interface_USB:CH340K', 'U', 'CH340K', (x, y), mpn='CH340K')
    sh.connect(ch, {'1': 'USB_DP', '2': 'USB_DM', '3': 'GND', '11': 'GND', '4': 'USB_DTR', '6': 'USB_RTS',
                    '7': '+3V3', '10': '+3V3', '8': 'U0_RX', '9': 'U0_TX'}, nc=['5'])
    C(sh, '100n', x - 33.02, y + 25.4, '+3V3', 'GND')
    C(sh, '10u', x - 33.02, y + 35.56, '+3V3', 'GND', 'C0805')

    # USB-C только USB 2.0: CC по 5,1 кОм на землю; VBUS на питание платы не идёт
    x, y = 330.2, 157.48
    sh.text('USB-C (прошивка и журнал). VBUS — только на защиту, платy не питает (DESIGN.md).', (x - 66.04, y - 30.48))
    j = sh.part('Connector:USB_C_Receptacle_USB2.0_16P', 'J', 'USB-C', (x, y),
                fp='Connector_USB:USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A')
    sh.connect(j, {'VBUS': 'USB_VBUS', 'CC1': 'USB_CC1', 'CC2': 'USB_CC2', 'D+': 'USB_DP', 'D-': 'USB_DM',
                   'GND': 'GND', 'SHIELD': 'GND'}, nc=['SBU1', 'SBU2'])
    R(sh, '5.1k', x - 60.96, y + 10.16, 'USB_CC1', 'GND')
    R(sh, '5.1k', x - 60.96, y + 20.32, 'USB_CC2', 'GND')
    e = sh.part('Power_Protection:USBLC6-2SC6', 'U', 'USBLC6-2SC6', (x - 60.96, y - 12.7), mpn='USBLC6-2SC6')
    sh.connect(e, {'I/O1': 'USB_DP', 'I/O2': 'USB_DM', 'VBUS': 'USB_VBUS', 'GND': 'GND'})

    # разъём UART0 для диагностики (не устанавливается)
    j = sh.part('Connector_Generic:Conn_01x03', 'J', 'UART0 (диагностика)', (x - 7.62, y + 50.8),
                fp='Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical', dnp=True)
    sh.connect(j, {'1': 'U0_TX', '2': 'U0_RX', '3': 'GND'})
    return sh
