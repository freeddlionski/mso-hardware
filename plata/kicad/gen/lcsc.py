"""Номера LCSC и MPN для всех позиций BOM.

Ключ — (значение детали в схеме, посадочное место без библиотеки). Генератор (build.py) заполняет поля LCSC и MPN
у каждой детали, где они не заданы явно, и печатает список позиций без номера.

Поле «осн.» — базовая деталь JLCPCB (без доплаты за загрузку катушки) по списку
github.com/CDFER/jlcpcb-parts-database, scraped/assembly-details.csv от 2026-11-14 («base»).
Наличие на складе меняется: перед заказом прогнать BOM через JLCPCB BOM Tool.
Номера микросхем, дискретных и защиты проверены по страницам lcsc.com / jlcpcb.com (2026-11-14). Резисторы
1k, 1.5k, 2.2k, 4.7k, 5.1k, 10k, 15k, 22k, 100k, 150k — по таблице базовых деталей JLC (machtmu DFM guide) и списку
CDFER; MPN у них — по системе обозначений UNI-ROYAL. Чего нет в таблице, то ещё не найдено (build.py печатает список).
"""

# (значение, посадочное место) : (LCSC, MPN, примечание)
PARTS = {
    # --- микросхемы ---
    ('TPS26631PWPR', 'HTSSOP-20-1EP_4.4x6.5mm_P0.65mm_EP3.4x6.5mm_Mask2.96x2.96mm_ThermalVias'):
        ('C2866319', 'TPS26631PWPR', 'TI'),
    ('LM61460AANRJRR', 'Texas_RJR_VQFN-HR-14_3.5x4mm'): ('C2864505', 'LM61460AANRJRR', 'TI'),
    ('LMR51430XDDCR', 'SOT-23-6'): ('C5185863', 'LMR51430XDDCR', 'TI'),
    ('ESP32-S3-WROOM-1U-N16R2', 'ESP32-S3-WROOM-1U'): ('C3013945', 'ESP32-S3-WROOM-1U-N16R2', 'Espressif'),
    ('CH340K', 'SSOP-10-1EP_3.9x4.9mm_P1mm_EP2.1x3.3mm'): ('C968586', 'CH340K', 'WCH'),
    ('USBLC6-2SC6', 'SOT-23-6'): ('C7519', 'USBLC6-2SC6', 'ST'),
    ('W5500', 'LQFP-48_7x7mm_P0.5mm'): ('C32843', 'W5500', 'WIZnet'),
    ('THVD2410DR', 'SOIC-8_3.9x4.9mm_P1.27mm'): ('C1849398', 'THVD2410DR', 'TI'),
    ('MAX3232EIDR', 'SOIC-16_3.9x9.9mm_P1.27mm'): ('C193666', 'MAX3232EIDR', 'TI; −40…+85 °C'),
    ('74AHCT1G125', 'SOT-23-5'): ('C7484', 'SN74AHCT1G125DBVR', 'TI'),
    ('EL357N(C)', 'SOP-4_3.8x4.1mm_P2.54mm'): ('C42379244', 'EL357N(C)(TA)-G', 'Everlight; C29981 — снят с новых разработок'),
    ('74HCT245', 'TSSOP-20_4.4x6.5mm_P0.65mm'): ('C5980', '74HCT245PW,118', 'Nexperia'),
    ('PCF8563T', 'SOIC-8_3.9x4.9mm_P1.27mm'): ('C7440', 'PCF8563T/5,518', 'NXP'),
    ('PCA9555PW', 'TSSOP-24_4.4x7.8mm_P0.65mm'): ('C128392', 'PCA9555PW,118', 'NXP'),
    ('74AHCT125', 'TSSOP-14_4.4x5mm_P0.65mm'): ('C148198', '74AHCT125PW,118', 'Nexperia'),

    # --- транзисторы, диоды, защита ---
    ('CSD19534Q5A', 'Texas_DQJ_VSONP-8_5x6mm_CSD19534Q5A'): ('C114200', 'CSD19534Q5A', 'TI'),
    ('2N7002', 'SOT-23'): ('C85049', '2N7002-7-F', 'Diodes Inc.'),
    ('MMBT3904', 'SOT-23'): ('C20526', 'MMBT3904', 'JSCJ, осн.'),
    ('DMN6140L', 'SOT-23'): ('C156306', 'DMN6140L-7', 'Diodes Inc.'),
    ('BAT46W', 'D_SOD-123'): ('C7420332', 'BAT46W', 'R+O, 100 В'),
    ('BAT54S', 'SOT-23'): ('C47546', 'BAT54S,215', 'Nexperia'),
    ('BAT54C', 'SOT-23'): ('C2135', 'BAT54C', 'JSCJ'),
    ('1N4148W', 'D_SOD-123'): ('C81598', '1N4148W', 'осн.'),
    ('SS34', 'D_SMA'): ('C8678', 'SS34', 'MDD, осн.'),
    ('4.7V', 'D_SOD-123'): ('C22395547', 'MMSZ4688', 'R+O, стабилитрон 4,7 В 500 мВт'),
    ('SMAJ33A', 'D_SMA'): ('C223988', 'SMAJ33A', 'Littelfuse'),
    ('SMAJ36CA', 'D_SMA'): ('C5249597', 'SMAJ36CA', 'ElecSuper'),
    ('SMAJ8.0CA', 'D_SMA'): ('C173500', 'SMAJ8.0CA', 'MDD; пробой 8,89–9,83 В, утечка ≤ 50 мкА при 8 В'),
    ('SMCJ33CA', 'D_SMC'): ('C224050', 'SMCJ33CA', 'Littelfuse'),
    ('600R@100MHz', 'L_0805_2012Metric'): ('C1017', '', 'ферритовая бусина 600 Ом 0805, осн.'),

    # --- разъёмы ---
    # 0…+70 °C — принято (Павел, 14.11: «пойдет 0 до 70 градусов»)
    ('RJ45 HR911105A', 'RJ45_Hanrun_HR911105A_Horizontal'): ('C12074', 'HR911105A', 'HanRun; 0…+70 °C'),

    # --- конденсаторы (напряжение — с запасом к цепи; X5R/X7R) ---
    ('100n', 'C_0603_1608Metric'): ('C14663', 'CC0603KRX7R9BB104', 'YAGEO 50 В X7R, осн.'),
    ('100n 50V', 'C_0603_1608Metric'): ('C14663', 'CC0603KRX7R9BB104', 'YAGEO 50 В X7R, осн.'),
    ('100n 100V', 'C_0603_1608Metric'): ('C15725', 'CL10B104KC8NNNC', 'Samsung 100 В X7R'),
    ('100n 100V', 'C_0805_2012Metric'): ('C344180', 'TCC0805X7R104K101DT', 'CCTC 100 В X7R'),
    ('10n', 'C_0603_1608Metric'): ('C57112', '0603B103K500NT', 'FH 50 В X7R, осн.'),
    ('22n', 'C_0603_1608Metric'): ('C277528', 'CC0603JRX7R9BB223', 'YAGEO 50 В X7R'),
    ('6.8n', 'C_0603_1608Metric'): ('C107097', 'CC0603KRX7R9BB682', 'YAGEO 50 В X7R'),
    ('18p', 'C_0603_1608Metric'): ('C1647', 'CL10C180JB8NNNC', 'Samsung 50 В C0G, осн.'),
    ('1u', 'C_0603_1608Metric'): ('C157684', '0603X105K500NT', 'FH 50 В'),
    ('4.7u', 'C_0805_2012Metric'): ('C1779', 'CL21A475KAQNNNE', 'Samsung 25 В, осн.'),
    ('10u', 'C_0805_2012Metric'): ('C1713', 'CL21A106KOQNNNE', 'Samsung 16 В; цепи 3,3 В'),
    ('22u', 'C_1206_3216Metric'): ('C90146', 'CL31A226KOHNNNE', 'Samsung 16 В; цепи 3,3 и 5 В'),
    ('22u', 'C_1210_3225Metric'): ('C52306', 'CL32A226KAJNNNE', 'Samsung 25 В; цепь 12 В'),
    ('10u 50V', 'C_1210_3225Metric'): ('C77102', 'GRM32ER71H106KA12L', 'Murata 50 В X7R; вход 24 В'),
    ('47u 10V', 'C_1210_3225Metric'): ('C76680', 'C3225X5R1A476MT000E', 'TDK 10 В X5R; табло 5 В'),

    # --- светодиоды 0603 (Vf ≈ 2 В: светятся и от 3,3 В через 2,2 кОм) ---
    ('зелёный', 'LED_0603_1608Metric'): ('C2289', 'KT-0603YG', 'KENTO, жёлто-зелёный'),
    ('зелёный RX', 'LED_0603_1608Metric'): ('C2289', 'KT-0603YG', 'KENTO, жёлто-зелёный'),
    ('красный TX', 'LED_0603_1608Metric'): ('C2286', '', 'красный 0603, осн.'),

    # --- самовосстанавливающиеся предохранители: все на 60 В (сработавший PTC держит полное напряжение линии,
    #     до 35,3 В — верхний порог OVP; детали на 30–33 В не годятся) ---
    ('50mA удерж.', 'Fuse_1206_3216Metric'): ('C315892', '1206L005/60WR', 'Littelfuse 60 В'),
    ('100mA удерж.', 'Fuse_1206_3216Metric'): ('C70065', 'nSMD010', 'TECHFUSE 60 В'),
    ('0.75A удерж.', 'Fuse_2920_7451Metric'): ('C207083', '2920L075/60MR', 'Littelfuse 60 В'),
    ('1.1A удерж.', 'Fuse_2920_7451Metric'): ('C315903', '2920L110/60MR', 'Littelfuse 60 В'),
    ('1.5A удерж.', 'Fuse_2920_7451Metric'): ('C6165178', 'SMD2920-150/60N', 'BORN 60 В'),

    ('5A удерж.', 'Fuse_2920_7451Metric'): ('C207091', '2920L500/16MR', 'Littelfuse 16 В; только цепи табло 5 В'),

    # --- дроссели ---
    ('10u', 'L_Taiyo-Yuden_NR-50xx'): ('C222949', 'NRS5040T100MMGJ', 'Taiyo Yuden 2,1 А, Isat 2,3 А; 12 В'),
    ('6.8u', 'L_Taiyo-Yuden_NR-50xx'): ('C222948', 'NRS5040T6R8MMGJ', 'Taiyo Yuden 2,4 А, Isat 2,8 А; 5 В'),
    ('4.7u', 'L_Taiyo-Yuden_NR-50xx'): ('C223064', 'NR5040T4R7N', 'Taiyo Yuden 3,1 А, Isat 3,3 А; 3,3 В'),
    # посадочное место — Bourns SRR1260 (12,5 × 12,5); у SRR1280A тот же габарит, площадки сверить по чертежу Bourns
    ('6.8u 8A', 'L_Bourns_SRR1260'): ('C2051060', 'SRR1280A-6R8Y', 'Bourns 7,6 А, Isat 8 А, 18,5 мОм; табло 5 В / 5 А'),

    # --- кварцы ---
    ('25MHz 20ppm', 'Crystal_SMD_3225-4Pin_3.2x2.5mm'): ('C9006', 'X322525MOB4SI', 'YXC, CL 12 пФ, осн.'),
    ('32.768kHz', 'Crystal_SMD_3215-2Pin_3.2x1.5mm'): ('C32346', 'Q13FC13500004', 'Epson, CL 12,5 пФ, осн.'),
    ('10p DNP', 'C_0603_1608Metric'): ('C1634', 'CL10C100JB8NNNC', 'Samsung C0G, осн.; не ставим'),
    ('1u 50V', 'C_1206_3216Metric'): ('C1848', 'CL31B105KBHNNNE', 'Samsung X7R, осн.'),
    ('470u 16V', 'CP_Elec_10x10.5'): ('C5289730', 'EMK1CM471GB0D00R', 'AISHI 105 °C; наличие проверить при заказе'),
    ('100u 50V', 'CP_Elec_10x10.5'): ('C5158069', 'MAL214699103E3', 'Vishay 105 °C; наличие проверить при заказе'),
    ('120', 'R_0805_2012Metric'): ('C17437', '0805W8F1200T5E', 'осн.'),
    ('150', 'R_0805_2012Metric'): ('C17471', '0805W8F1500T5E', 'осн.'),
    ('680 DNP', 'R_0603_1608Metric'): ('C23228', '0603WAF6800T5E', 'осн.; не ставим'),
    # --- внутренние разъёмы ---
    ('Табло 1: +5V / GND', 'Molex_Mini-Fit_Jr_5566-02A_2x01_P4.20mm_Vertical'): ('C20539146', 'HC-5566-2*1A-05', 'HCTL, аналог Molex 5566-02A; сверить отверстия'),
    ('Табло 2: +5V / GND', 'Molex_Mini-Fit_Jr_5566-02A_2x01_P4.20mm_Vertical'): ('C20539146', 'HC-5566-2*1A-05', 'HCTL, аналог Molex 5566-02A; сверить отверстия'),
    ('MDB Mini-Fit Jr 2×3', 'Molex_Mini-Fit_Jr_5566-06A_2x03_P4.20mm_Vertical'): ('C20539148', 'HC-5566-2*3A-05', 'HCTL, аналог Molex 5566-06A; сверить отверстия'),
    ('HUB75 IDC-16', 'IDC-Header_2x08_P2.54mm_Vertical'): ('C3406', '2.54-2*8P box header', 'BOOMELE, вилка с кожухом'),
    ('UART0 (диагностика)', 'PinHeader_1x03_P2.54mm_Vertical'): ('C49257', '2.54-1*3P', 'BOOMELE; не ставим'),
    ('Терминатор 120 Ом', 'PinHeader_1x02_P2.54mm_Vertical'): ('C492401', 'PZ254V-11-02P', 'XFCN'),
    ('Резерв PCA9555 P1.0–P1.7', 'PinHeader_2x05_P2.54mm_Vertical'): ('C492422', 'PZ254V-12-10P', 'XFCN; не ставим'),

    # --- клеммы: разъёмные колодки KANGNEX (аналог Phoenix MC 1,5/…-G-3,81 и MSTBA 2,5/…-G-5,08).
    #     Ответные вилки с винтами (15EDGK / 2EDGK) в монтаж не входят — заказываются к жгутам.
    #     Перед разводкой сверить шаг, диаметр отверстий и выступ корпуса с посадочным местом Phoenix в KiCad.
    ('RS-485: A / B / GND', 'KANGNEX_WJ15EDGRC_1x03_P3.81mm_Drill1.4'): ('C8406', 'WJ15EDGRC-3.81-03P-14-00A', 'KANGNEX, вилка 15EDGK-3.81'),
    ('Vendotek RS-232: TXD / RXD / GND', 'KANGNEX_WJ15EDGRC_1x03_P3.81mm_Drill1.4'): ('C8406', 'WJ15EDGRC-3.81-03P-14-00A', 'KANGNEX, вилка 15EDGK-3.81'),
    ('Монетник: +12V / GND / ИМП / БЛОК', 'KANGNEX_WJ15EDGRC_1x04_P3.81mm_Drill1.4'): ('C7245', 'WJ15EDGRC-3.81-04P-14-00A', 'KANGNEX, вилка 15EDGK-3.81'),
    ('Купюрник имп.: +24V / +12V / GND / ИМП', 'KANGNEX_WJ15EDGRC_1x04_P3.81mm_Drill1.4'): ('C7245', 'WJ15EDGRC-3.81-04P-14-00A', 'KANGNEX, вилка 15EDGK-3.81'),
    ('Сервис: КН / GND', 'KANGNEX_WJ15EDGRC_1x02_P3.81mm_Drill1.4'): ('C8387', 'WJ15EDGRC-3.81-02P-14-00A', 'KANGNEX, вилка 15EDGK-3.81'),
    ('Входы: ВХ1–ВХ4 / GND / GND', 'KANGNEX_WJ15EDGRC_1x06_P3.81mm_Drill1.4'): ('C7246', 'WJ15EDGRC-3.81-06P-14-00A', 'KANGNEX, вилка 15EDGK-3.81'),
    ('Выходы: +24V / ВЫХ1–ВЫХ4 / GND', 'KANGNEX_WJ15EDGRC_1x06_P3.81mm_Drill1.4'): ('C7246', 'WJ15EDGRC-3.81-06P-14-00A', 'KANGNEX, вилка 15EDGK-3.81'),
    ('Питание +24V / GND', 'KANGNEX_WJ2EDGRC_1x02_P5.08mm_Drill1.7'): ('C3697', 'WJ2EDGRC-5.08-02P-14-00A', 'KANGNEX 10 А, вилка 2EDGK-5.08'),
    ('Vendotek: +24V / GND', 'KANGNEX_WJ2EDGRC_1x02_P5.08mm_Drill1.7'): ('C3697', 'WJ2EDGRC-5.08-02P-14-00A', 'KANGNEX 10 А, вилка 2EDGK-5.08'),

    ('USB-C', 'USB_C_Receptacle_HCTL_HC-TYPE-C-16P-01A'): ('C2894897', 'HC-TYPE-C-16P-01A', 'HCTL'),
    ('CR2032', 'BatteryHolder_MYOUNG_BS-07-A1BJ001_CR2032'): ('C2979167', 'BS-07-A1BJ001', 'MYOUNG, −25…+85 °C'),
    ('7.5A', 'Fuseholder_Blade_Mini_Keystone_3568'): ('C5249699', '3568', 'Keystone; вставка mini-blade 7,5 А — к жгуту/в ЗИП'),

    ('RESET', 'SW_SPST_TL3342'): ('C2886898', 'TL3342F160QG', 'E-Switch, −20…+70 °C; наличие на LCSC проверить перед заказом'),
    ('BOOT', 'SW_SPST_TL3342'): ('C2886898', 'TL3342F160QG', 'E-Switch, −20…+70 °C; наличие на LCSC проверить перед заказом'),
    ('СЕРВИС', 'SW_SPST_TL3342'): ('C2886898', 'TL3342F160QG', 'E-Switch, −20…+70 °C; наличие на LCSC проверить перед заказом'),

    # --- резисторы 0603 (UNI-ROYAL 0603WAF, ±1 %, 75 В) ---
    ('0', 'R_0603_1608Metric'): ('C21189', '0603WAF0000T5E', 'осн.'),
    ('10', 'R_0603_1608Metric'): ('C22859', '0603WAF100JT5E', 'осн.'),
    ('33', 'R_0603_1608Metric'): ('C23140', '0603WAF330JT5E', 'осн.'),
    ('82', 'R_0603_1608Metric'): ('C23255', '0603WAF820JT5E', ''),
    ('100', 'R_0603_1608Metric'): ('C22775', '0603WAF1000T5E', 'осн.'),
    ('330', 'R_0603_1608Metric'): ('C23138', '0603WAF3300T5E', 'осн.'),
    ('1k', 'R_0603_1608Metric'): ('C21190', '0603WAF1001T5E', 'осн.'),
    ('1.5k', 'R_0603_1608Metric'): ('C22843', '0603WAF1501T5E', 'осн.'),
    ('2.2k', 'R_0603_1608Metric'): ('C4190', '0603WAF2201T5E', 'осн.'),
    ('4.7k', 'R_0603_1608Metric'): ('C23162', '0603WAF4701T5E', 'осн.'),
    ('5.1k', 'R_0603_1608Metric'): ('C23186', '0603WAF5101T5E', 'осн.'),
    ('10k', 'R_0603_1608Metric'): ('C25804', '0603WAF1002T5E', 'осн.'),
    ('15k 1%', 'R_0603_1608Metric'): ('C22809', '0603WAF1502T5E', 'осн.'),
    ('22k', 'R_0603_1608Metric'): ('C31850', '0603WAF2202T5E', 'осн.'),
    ('100k', 'R_0603_1608Metric'): ('C25803', '0603WAF1003T5E', 'осн.'),
    ('100k 1%', 'R_0603_1608Metric'): ('C25803', '0603WAF1003T5E', 'осн.'),
    ('150k', 'R_0603_1608Metric'): ('C22807', '0603WAF1503T5E', 'осн.'),
    ('1M', 'R_0603_1608Metric'): ('C22935', '0603WAF1004T5E', 'осн.'),
    ('2.2k 1W', 'R_2512_6332Metric'): ('C453411', 'RC-12K2201FT', 'FH, 1 Вт, ±1 %'),
    ('8.66k', 'R_0603_1608Metric'): ('C23114', '0603WAF8661T5E', ''),
    ('3k 1%', 'R_0603_1608Metric'): ('C4211', '0603WAF3001T5E', 'осн.'),
    ('49.9 1%', 'R_0603_1608Metric'): ('C23185', '0603WAF499JT5E', 'осн.'),
    ('5.23k 1%', 'R_0603_1608Metric'): ('C23068', '0603WAF5231T5E', ''),
    ('12.4k 1%', 'R_0603_1608Metric'): ('C22865', '0603WAF1242T5E', ''),
    ('13.7k 1%', 'R_0603_1608Metric'): ('C22793', '0603WAF1372T5E', ''),
    ('19.1k 1%', 'R_0603_1608Metric'): ('C22897', '0603WAF1912T5E', ''),
    ('22.1k 1%', 'R_0603_1608Metric'): ('C2960862', 'FRC0603F2212TS', 'FOJAN'),
    ('24.9k 1%', 'R_0603_1608Metric'): ('C137761', 'RC0603FR-0724K9L', 'YAGEO'),
    ('33.2k 1%', 'R_0603_1608Metric'): ('C185338', 'RC0603FR-0733K2L', 'YAGEO'),
    ('390k 1%', 'R_0603_1608Metric'): ('C23150', '0603WAF3903T5E', ''),
}


def fp_short(fp):
    return fp.split(':', 1)[-1]


def apply(proj):
    """Заполнить LCSC/MPN; вернуть список позиций без номера (значение, посадочное место, позиции)."""
    missing = {}
    for sh in proj.sheets:
        for p in sh.parts:
            if p.ref.startswith('#') or p.lcsc:
                continue
            fp = p.fp
            if not fp:
                from sexp import findall
                fp = next((str(x[2]) for x in findall(p.sym, 'property') if x[1] == 'Footprint'), '')
            key = (p.value, fp_short(fp))
            if key in PARTS:
                p.lcsc, mpn, _ = PARTS[key]
                if mpn and not p.mpn:
                    p.mpn = mpn
            else:
                missing.setdefault(key, []).append(p.ref)
    return missing
