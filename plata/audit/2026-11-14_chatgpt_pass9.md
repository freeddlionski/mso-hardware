# Pass 9 — RTL8305NB Ethernet switch (read-only audit)

Дата: 2026-11-14. База: main 2041a1bc844d8cd0a23ada1ae9a3294e66dcecd7.
Схема и исходники НЕ изменялись. **Аудит частичный.**

## 1. RTL8305NB: все 49 выводов против Table 1

Сравнено с Realtek RTL8305NB-VB Datasheet Rev 1.0, Track ID JATR-8275-15, Table 1, стр. 6:
https://resources.ampheo.com/static/datasheets/realtek/rtl8305nb-vb-cg.pdf

Исходник: plata/kicad/gen/custom_syms.py, ic('RTL8305NB', ...).

| Номер | Даташит | Символ | Итог |
|---|---|---|---|
| 1 | AVDDL | AVDDL | OK |
| 2 | RXIP1 | RXIP1 | OK |
| 3 | RXIN1 | RXIN1 | OK |
| 4 | TXON1 | TXON1 | OK |
| 5 | TXOP1 | TXOP1 | OK |
| 6 | AVDDH | AVDDH | OK |
| 7 | DVDDL | DVDDL | OK |
| 8 | AVDDH | AVDDH | OK |
| 9 | TXOP2 | TXOP2 | OK |
| 10 | TXON2 | TXON2 | OK |
| 11 | RXIN2 | RXIN2 | OK |
| 12 | RXIP2 | RXIP2 | OK |
| 13 | AVDDL | AVDDL | OK |
| 14 | RXIP3 | RXIP3 | OK |
| 15 | RXIN3 | RXIN3 | OK |
| 16 | TXON3 | TXON3 | OK |
| 17 | TXOP3 | TXOP3 | OK |
| 18 | AVDDH | AVDDH | OK |
| 19 | TXOP4 | TXOP4 | OK |
| 20 | TXON4 | TXON4 | OK |
| 21 | RXIN4 | RXIN4 | OK |
| 22 | RXIP4 | RXIP4 | OK |
| 23 | AVDDL | AVDDL | OK |
| 24 | DVDDL | DVDDL | OK |
| 25 | SCL/MDC | SCL/MDC | OK |
| 26 | SDA/MDIO | SDA/MDIO | OK |
| 27 | RESETB | RESETB | OK |
| 28 | LDIND/DIS_LD | LDIND/DIS_LD | OK |
| 29 | P0LED/DIS_EEE | P0LED/DIS_EEE | OK |
| 30 | P1LED | P1LED | OK |
| 31 | DVDDH | DVDDH | OK |
| 32 | P2LED/DIS_RST_BLNK | P2LED/DIS_RST_BLNK | OK |
| 33 | P3LED | P3LED | OK |
| 34 | P4LED | P4LED | OK |
| 35 | DVDDL | DVDDL | OK |
| 36 | V12OUT | V12OUT | OK |
| 37 | V33IN | V33IN | OK |
| 38 | AVDDHPLL | AVDDHPLL | OK |
| 39 | XO | XO | OK |
| 40 | XI | XI | OK |
| 41 | AVDDLPLL | AVDDLPLL | OK |
| 42 | IBREF | IBREF | OK |
| 43 | AVDDL | AVDDL | OK |
| 44 | RXIP0 | RXIP0 | OK |
| 45 | RXIN0 | RXIN0 | OK |
| 46 | TXON0 | TXON0 | OK |
| 47 | TXOP0 | TXOP0 | OK |
| 48 | AVDDH | AVDDH | OK |
| E-PAD | E-PAD | EP | OK |

Итого: 48/48 внешних выводов плюс exposed pad совпадают по номеру и имени. Номер «49» для EP — условная нумерация KiCad; в даташите площадка называется E-PAD.

## 2. Схема RTL8305NB против PDF-образца

**Ограничение:** файл plata/ref/RTL8305NB_switch_reference_2022-08-13.pdf обнаружен в GitHub (410834 байт); получено бинарное содержимое base64, но графические страницы прочитать не удалось. Поэтому **сравнение с образцом не выполнено ни по одному пункту**. Ниже только факты из исходника и независимая сверка с даташитом; эти строки НЕ являются перечнем отличий от PDF.

| Узел | Факт по sheet_eth.py | Оценка | Сравнение с PDF |
|---|---|---|---|
| RJ45 LAN, порт 1 | RX± → 1/2, TX± → 3/6 | Допустимо по логическим именам; внутренний pinout HR911105A не подтверждён | не открылся |
| RJ45 Vendotek, порт 2 | RX± → 1/2, TX± → 3/6 | То же | не открылся |
| RJ45 CT | 4 и 5 объединены, 100 нФ к GND | Требуется сверить pinout и рекомендации по termination | не открылся |
| 3,3 В | V33IN, AVDDH×4, AVDDHPLL, DVDDH → +3V3; 10u+1u+7×100n | Логика питания соответствует Realtek Table 7; топология PCB не проверена | не открылся |
| V12OUT / ядро | V12OUT, AVDDL×4, AVDDLPLL, DVDDL×3 → SW_1V0; 220u+1u+9×100n | **Исправить название: 1,2 В, не 1,0 В**; Table 6, §7.3.9 | не открылся |
| IBREF | 2,49 кОм 1% к GND | Соответствует Realtek Table 3 | не открылся |
| Кварц | 25 МГц, 2×18 пФ | Частота правильная; ESR ≤30 Ом и CL кварца не проверены | не открылся |
| RESETB | 10 кОм на 3,3 В, 1 мкФ на GND | Проверить Td после стабилизации обеих шин, а не только RC≈10 мс | не открылся |
| LED порт 1 | P1LED через 330 Ом на RJ45; другой LED от W5500 ACTLED | Проверить полярность и информативность | не открылся |
| LED порт 2 | P2LED/DIS_RST_BLNK через 330 Ом | Проверить strap на сбросе и полярность | не открылся |
| Straps | P0LED/DIS_EEE, LDIND/DIS_LD, SCL/MDC, SDA/MDIO — NC | Проверить желаемые режимы и встроенные pull-up/down | не открылся |
| Порты 3–4 | PHY TX/RX NC | Проверить рекомендацию производителя для неиспользуемых PHY | не открылся |

**Подтверждённая находка — серьёзная документационная ошибка:** название сети SW_1V0 и текст «1,0 В» неверны. Realtek описывает V12OUT как 1,2 В. Это не доказывает неверное фактическое напряжение, но может привести к ошибкам при дальнейшей работе.

## 3. W5500 ↔ H1102 ↔ RTL8305NB, порт 0

Исходник: plata/kicad/gen/sheet_eth.py, build().

W5500 TXP/TXN → трансформатор 1/3, CT=2. W5500 RXP/RXN после 6,8 нФ → 6/8, CT=7.
RTL RXIP0/RXIN0 → 16/14, CT=15 через 100 нФ к GND.
RTL TXOP0/TXON0 → 11/9, CT=10 через 100 нФ к GND.

**Направления TX→RX, RX←TX в именах цепей не перепутаны.** Но это не подтверждает реальную фазировку обмоток H1102N.

**Блокер проверки:** PHY—трансформатор—PHY принципиально возможен, но в этой реализации не доказаны согласование, DC-смещение, common-mode и работа автосогласования на стороне RTL. Два конденсатора 100 нФ от CT к GND сами по себе не доказывают корректную аналоговую нагрузку. Нужны оригинальные схемы магнитики и рекомендованная цепь RTL; затем измерение на прототипе 10/100 Мбит/с, link-up при сбросах и передача пакетов. **Нельзя объявить схему рабочей только по TX/RX.**

## 4. Посадочные места

| Компонент | Подтверждено | Не подтверждено | Итог |
|---|---|---|---|
| CND-tek H1102N, LCSC C42418465 | LCSC/JLCPCB: SMD-16P 12,7×7 мм, 1:1, 100M; в коде Transformer_SMD:Transformer_Ethernet_CNDtek_H1102N | Оригинальный mechanical drawing, шаг/размеры pad, pin 1, нумерация и фазировка; совместимость с символом Transformer:Wuerth_749013011A | **НЕ ПРОВЕРЕНО полностью** |
| RTL8305NB-VB-CG, LCSC C3010343 | В коде Package_DFN_QFN:QFN-48-1EP_6x6mm_P0.4mm_EP4.4x4.4mm; заявленные корпус/шаг соответствуют обозначению | Оригинальный land pattern, размеры pad, thermal pad и паста | **НЕ ПРОВЕРЕНО полностью** |

Источники: https://www.lcsc.com/product-detail/C42418465.html ; https://www.lcsc.com/product-detail/C3010343.html . Имя footprint само по себе не является геометрической верификацией.

## Исправить до разводки

| Приоритет | Действие |
|---|---|
| Исправить | SW_1V0 → SW_1V2; «1,0 В» → «1,2 В» в комментариях и надписях |
| Блокер | Прочитать и сравнить поэлементно оригинальный plata/ref/RTL8305NB_switch_reference_2022-08-13.pdf; в этом проходе он НЕ ПРОЧИТАН |
| Блокер | Сверить H1102N по datasheet: обмотки, номера 1–16, фазировку, символ Wuerth и footprint CND-tek |
| Блокер | Обосновать согласование и смещение PHY↔PHY через один трансформатор; подтвердить работу порта 0 |
| Блокер | Сверить реальные чертежи land pattern C42418465 и C3010343 |
| Желательно | Проверить straps/LED, reset timing, кварц и режимы неиспользуемых портов |

**Вердикт:** распиновка символа PASS; обвязка относительно эталона NOT VERIFIED; соединение PHY↔PHY NOT VERIFIED; footprint NOT VERIFIED. До разводки закрыть блокеры.