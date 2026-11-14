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
    # MAX13223EEUP+ (C143338) на складе LCSC нет; вариант в ленте +T — единицы штук. Риск поставки, см. DESIGN «Открыто».
    ('MAX13223EEUP+', 'TSSOP-20_4.4x6.5mm_P0.65mm'): ('C118523', 'MAX13223EEUP+T', 'ADI; мало на складе'),
    ('74AHCT1G125', 'SOT-23-5'): ('C7484', 'SN74AHCT1G125DBVR', 'TI'),
    ('EL357N(C)', 'SOP-4_3.8x4.1mm_P2.54mm'): ('C42379244', 'EL357N(C)(TA)-G', 'Everlight; C29981 — снят с новых разработок'),
    ('74HCT245', 'TSSOP-20_4.4x6.5mm_P0.65mm'): ('C5980', '74HCT245PW,118', 'Nexperia'),
    ('PCF8563T', 'SOIC-8_3.9x4.9mm_P1.27mm'): ('C7440', 'PCF8563T/5,518', 'NXP'),
    ('PCA9555PW', 'TSSOP-24_4.4x7.8mm_P0.65mm'): ('C128392', 'PCA9555PW,118', 'NXP'),
    ('74AHCT125', 'TSSOP-14_4.4x5mm_P0.65mm'): ('C148198', '74AHCT125PW,118', 'Nexperia'),

    # --- транзисторы, диоды, защита ---
    ('CSD19534Q5A', 'TDSON-8-1'): ('C114200', 'CSD19534Q5A', 'TI'),
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
    ('SMCJ33CA', 'D_SMC'): ('C224050', 'SMCJ33CA', 'Littelfuse'),
    ('600R@100MHz', 'L_0805_2012Metric'): ('C1017', '', 'ферритовая бусина 600 Ом 0805, осн.'),

    # --- разъёмы ---
    # HR911105A: рабочая температура 0…+70 °C — для мойки мало, замена на решении (DESIGN «Открыто»)
    ('RJ45 HR911105A', 'RJ45_Hanrun_HR911105A_Horizontal'): ('C12074', 'HR911105A', 'HanRun; 0…+70 °C'),

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
