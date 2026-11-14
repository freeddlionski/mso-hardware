# МСО74 — аудит платы, проход 6 (частичный результат)

Основа: архив mso-hardware_main.zip, заявленный main 5f1c209, экспорт netlist/XML, bom.csv, DESIGN.md §2, plata/audit/pass5/results/ic_pins.csv. **Схема и плата не изменялись. Проверка НЕ завершена; этот PR не означает допуск к производству.**

## Подтверждено первоисточниками

1. **U10 W5500, LQFP-48.** WIZnet, *W5500 Datasheet v1.0.9*, §1.1, Table 2, pp.8–10; revision history p.65. Вывод 7 DNC — NC, 18 VBG — должен быть floating, 23 RSVD — GND, 38–42 RSVD — NC (поправка v1.0.2). По ic_pins.csv схема соответствует именно этим требованиям: 7,18,38–42 свободны, 23 на GND. NC 12,13,46,47 также свободны. SPDLED 24 и DUPLED 26 — незадействованные выходы. Источник: https://docs.wiznet.io/img/products/w5500/w5500_ds_v109e.pdf

2. **U1 TPS26631PWPR, HTSSOP-20.** Texas Instruments, *TPS2663x 60V, 6A Power Limiting, Surge Protection Industrial eFuse*, SLVSE94G, revised June 2024, §5, Table 5-1, p.4. IMON pin14, FLT pin15, PGOOD pin17 допускается оставить floating; именно так в netlist. Проверены также номера 10 dVdT, 11 ILIM, 12 MODE, 13 SHDN, 16 PGTH, 18–20 OUT. Полная проверка всех выводов/EP не завершена. https://www.ti.com/lit/ds/symlink/tps2663.pdf

3. **U11 THVD2410DR, SOIC-8.** Texas Instruments, *THVD24x0 ±70-V Fault-Protected RS-485 Transceivers*, SLLSF20B, revised October 2021, §6.1 Absolute Maximum Ratings, p.4. Bus A/B −70…+70 В; схема: pin6 A=RS485_A, pin7 B=RS485_B, pin8 VCC=+3V3, pin5 GND=GND. При +32 В DC запас до +70 В **38 В** (не гарантия работоспособности и не импульсная стойкость всей линии). Ambient −40…+125 °C, p.1. https://www.ti.com/lit/ds/symlink/thvd2410.pdf

4. **U5/U6 LM61460AANRJRR.** Texas Instruments, *LM61460 Datasheet Rev. D*, RJR0014A Package Outline, drawing 4223976/H (June 2026): VQFN-HR-14, корпус 3.4–3.6 × 3.9–4.1 мм. По TI product page рабочая температура −40…+150 °C. Название пользовательской footprint mso74:Texas_RJR_VQFN-HR-14_3.5x4mm согласуется с габаритом корпуса, но **совпадение площадок/EP/land pattern не подтверждено**. https://www.ti.com/lit/ds/symlink/lm61460.pdf ; https://www.ti.com/product/LM61460/part-details/LM61460AANRJRR

5. **CSD19534Q5A.** Texas Instruments, product/packaging: VSONP DQJ, 8 pins, 5×6 мм, −55…+150 °C. DNK и соответствие KiCad TDSON-8-1 не подтверждены. https://www.ti.com/product/CSD19534Q5A

6. **KiCad footprint SOP-4_3.8x4.1mm_P2.54mm.** Официальный GitLab master, файл генератора 2026-02-06 (не зафиксирован релиз KiCad 9): pad 1 (−2.75,−1.27), 2 (−2.75,+1.27), 3 (+2.75,+1.27), 4 (+2.75,−1.27) мм; размер каждого 1.45×0.55 мм. Чертёж производителя EL357N(C) для сравнения не проверен. https://gitlab.com/kicad/libraries/kicad-footprints/-/raw/master/Package_SO.pretty/SOP-4_3.8x4.1mm_P2.54mm.kicad_mod

## Найденные риски

- **Критично, подтверждено netlist (проход 5):** J17.1–8 напрямую к U20 PCA9555 pins 13–20, J17.9 напрямую к +3V3. Требование DESIGN.md §2 «+32 В на полевой сигнал безопасно» не выполняется для этих прямых цепей. Производственные испытания до исправления опасны.
- **Производственный блокер:** U5/U6 используют пользовательскую footprint mso74:Texas_RJR_VQFN-HR-14_3.5x4mm; нужно подтвердить pad-by-pad по чертежу TI и фактической библиотеке/Gerber. В проходе 5 ERC отмечал отсутствие библиотеки mso74.
- **Неопределённость:** U8 CH340K footprint SSOP-10-1EP_3.9x4.9mm_P1mm_EP2.1x3.3mm: в ic_pins.csv 10 выводов + pin11 GND (EP). Соответствие EP корпусу производителя не подтверждено. Файл официального GitLab для SSOP-10-1EP не удалось загрузить.

## Не найдено / не проверено — без догадок

**Полная pin-by-pin сверка:** LMR51430XDDC, ESP32-S3-WROOM-1U, CH340K, MAX13223E, PCA9555PW, PCF8563T, 74HCT245PW, 74AHCT125PW, SN74AHCT1G125DBV, USBLC6-2SC6, EL357N(C), 2N7002-7-F, MMBT3904, DMN6140L-7, BAT54S, BAT54C, BAT46W, SS34, SMAJ33A, SMCJ33CA, HR911105A (включая LED и shield). Остальные контакты TPS26631, LM61460, THVD2410 и W5500 также не все проверены.

**Land pattern:** RJR0014A — нет точных координат и размеров каждой площадки; CSD19534Q5A DQJ vs TDSON-8-1; EL357N vs SOP-4; CH340K vs SSOP-10-1EP — сравнения с производителем не завершены.

**Температура:** полный BOM не верифицирован по MPN. HR911105A 0…+70 °C и равноразмерная замена с магнитами/LED не подтверждены первоисточником.

**Absolute maximum:** MAX13223E, DMN6140L, PCA9555, ESP32-S3 GPIO, CH340K — нет полной таблицы, запасов и оценки +32 В с выключенным питанием.

**Вердикт:** проход 6 частично выполнен, не считать схему проверенной и не отправлять в производство на основании этого PR.
