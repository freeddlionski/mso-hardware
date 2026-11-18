"""Спецификация компонентов для сборки (Excel) — для заводов в России (Резонит, pcbrussia).

python3 spec.py BOARD.kicad_pcb OUT.xlsx [PNP.csv]

Источник — разведённая плата (поля Value, MPN, LCSC, атрибуты dnp / exclude_from_bom) и примечания lcsc.py
(производитель). Одна строка на номер LCSC. Листы: «Спецификация» (ставим), «Не устанавливать» (DNP и не компоненты).
PNP.csv — координаты установки: начало — левый нижний угол платы, ось Y вверх, мм; поворот — как в KiCad
(против часовой); только устанавливаемые детали. Число паек — по площадкам посадочного места (SMD и выводные отдельно): по нему заводы считают монтаж.
"""
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

sys.path.insert(0, str(Path(__file__).parent))
from sexp import parse, find, findall  # noqa: E402
import lcsc  # noqa: E402

REV = 'A'
TITLE = 'Плата контроллера МСО74'
AUTHOR = 'Кольман Павел · mso74.ru · kolman74@mso74.ru'

KIND = {'R': 'Резистор', 'C': 'Конденсатор', 'L': 'Дроссель силовой', 'FB': 'Бусина ферритовая', 'D': 'Диод',
        'U': 'Микросхема', 'Q': 'Транзистор', 'J': 'Соединитель', 'F': 'Предохранитель самовосстанавливающийся',
        'Y': 'Резонатор кварцевый', 'SW': 'Кнопка тактовая', 'BT': 'Держатель батареи CR2032',
        'T': 'Трансформатор Ethernet', 'JP': 'Вилка штыревая (перемычка)'}

# производитель по началу MPN, где в lcsc.py его нет
MAKER_BY_MPN = [('0603WAF', 'UNI-ROYAL'), ('0603WAD', 'UNI-ROYAL'), ('0805W8F', 'UNI-ROYAL'), ('RC0603', 'YAGEO'),
                ('KT-0603', 'KENTO'), ('SS34', 'MDD')]
# ТКЕ по системе обозначений производителя, где его нет в примечании
DIEL = [(r'^CL\d\dA', 'X5R'), (r'^CL\d\dB', 'X7R'), (r'^CL\d\dC', 'C0G'), (r'^\d{4}B\d', 'X7R'), (r'^\d{4}X\d', 'X5R'),
        (r'^GRM\w{4}R7', 'X7R')]
# разъёмы и кнопки: тип по посадочному месту
JTYPE = [('WJ15EDGRC_1x0', 'Клеммник разъёмный, вилка {n} конт., шаг 3,81 мм (ответная часть 15EDGK)'),
         ('WJ2EDGRC_1x0', 'Клеммник разъёмный, вилка {n} конт., шаг 5,08 мм (ответная часть 2EDGK)'),
         ('MKDS', 'Клеммник винтовой {n} конт., шаг 5,08 мм'), ('RJ45', 'Розетка RJ45 угловая со светодиодами'),
         ('Mini-Fit', 'Вилка Mini-Fit Jr 2×3, шаг 4,2 мм, вертикальная'), ('IDC-Header_2x08', 'Вилка IDC-16 с кожухом, 2,54 мм'),
         ('USB_C', 'Розетка USB Type-C 16 конт.'), ('PinHeader_1x02', 'Вилка штыревая 2 конт., 2,54 мм')]
NOT_MAKER = {'осн.', 'ферритовая', 'красный', 'тот'}

SIZE = re.compile(r'(?:^|_)(0402|0603|0805|1206|1210|2512|2920)_')


def nat(ref):
    m = re.match(r'([A-Z]+)(\d+)', ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def refs_text(refs):
    """R1, R2, R3, R5 → R1–R3, R5"""
    refs = sorted(refs, key=nat)
    out, i = [], 0
    while i < len(refs):
        j = i
        while j + 1 < len(refs) and nat(refs[j + 1])[0] == nat(refs[i])[0] and nat(refs[j + 1])[1] == nat(refs[j])[1] + 1:
            j += 1
        out.append(refs[i] if j == i else (f'{refs[i]}, {refs[j]}' if j == i + 1 else f'{refs[i]}–{refs[j]}'))
        i = j + 1
    return ', '.join(out)


def notes_by_lcsc():
    return {l: (m, n) for (_v, _f), (l, m, n) in lcsc.PARTS.items()}


def maker(mpn, note):
    first = re.split(r'[,;]', note or '')[0].strip().split(' ')[0] if note else ''
    if first and first not in NOT_MAKER and re.match(r'[A-Za-z]', first):
        return {'Diodes': 'Diodes Inc.', 'R+O': 'R+O (Rectron)'}.get(first, first)
    for p, mk in MAKER_BY_MPN:
        if mpn.startswith(p):
            return mk
    return ''


def ohms(v):
    v = v.replace(',', '.')
    m = re.match(r'([\d.]+)\s*([kM]?)', v)
    num, mult = m.group(1).rstrip('.'), m.group(2)
    num = num.replace('.', ',')
    return f'{num} {"кОм" if mult == "k" else "МОм" if mult == "M" else "Ом"}'


def farads(v):
    m = re.match(r'([\d.]+)\s*([pnu])', v)
    return f'{m.group(1).replace(".", ",")} {dict(p="пФ", n="нФ", u="мкФ")[m.group(2)]}'


def describe(pre, value, fp, mpn, note, ref):
    """Наименование и параметры по-русски."""
    size = (SIZE.search(fp + '_') or [None, ''])[1] if SIZE.search(fp + '_') else ''
    note = note or ''
    if pre == 'R':
        tol = '±0,5 %' if 'WAD' in mpn else '±1 %'   # UNI-ROYAL: «J» в коде номинала — множитель 0,1, не допуск
        pw = {'0603': '0,1 Вт', '0805': '0,125 Вт', '2512': '1 Вт'}.get(size, '')
        return 'Резистор', f'{ohms(value.split()[0])} {tol} {pw}'.strip()
    if pre == 'C':
        if fp.startswith('CP_'):
            v = re.search(r'(\d+)\s*В', note) or re.search(r'(\d+)V', value)
            return 'Конденсатор алюминиевый электролитический', f'{farads(value)} {v.group(1)} В, 105 °C'
        v = re.search(r'(\d+)\s*В', note) or re.search(r'(\d+)V', value)
        d = re.search(r'X7R|X5R|C0G|NP0', note + ' ' + mpn)
        d = d.group(0) if d else next((t for rx, t in DIEL if re.match(rx, mpn)), '')
        kv = re.search(r'(\d+)kV', value)
        volt = f'{kv.group(1)} кВ' if kv else (f'{v.group(1)} В' if v else '')
        return 'Конденсатор керамический', ' '.join(x for x in (farads(value), volt, d) if x)
    if pre == 'L':
        m = re.search(r'(\d+(?:[.,]\d+)?) А, Isat ([\d,.]+) А', note)
        return 'Дроссель силовой', f'{farads(value).replace("мкФ", "мкГн")}' + (f', {m.group(1)} А (Isat {m.group(2)} А)' if m else '')
    if pre == 'FB':
        return 'Бусина ферритовая', '600 Ом при 100 МГц'
    if pre == 'F':
        if ref == 'F1':
            return 'Держатель предохранителя mini-blade (ATM)', 'вставка 7,5 А — НЕ устанавливать'
        return 'Предохранитель самовосстанавливающийся', f'ток удержания {value.split()[0].replace("mA", " мА").replace("A", " А").replace(".", ",")}, 60 В'
    if pre == 'D':
        if mpn.startswith('KT-0603') or 'LED' in fp:
            col = 'красный' if 'красн' in value else 'жёлто-зелёный'
            return 'Светодиод', col
        if 'SMAJ' in mpn or 'SMCJ' in mpn:
            return 'Диод TVS (супрессор)', ('двунаправленный' if mpn.endswith('CA') else 'однонаправленный') + f', {mpn}'
        if mpn.startswith('MMSZ'):
            return 'Стабилитрон', '4,7 В 0,5 Вт'
        if mpn.startswith('BAT') or mpn.startswith('SS'):
            return 'Диод Шоттки', mpn + (' (сборка)' if 'SOT' in fp else '')
        return 'Диод', mpn
    if pre == 'Y':
        return 'Резонатор кварцевый', value.replace('MHz', ' МГц').replace('kHz', ' кГц').replace('.', ',').replace(' 20ppm', ', ±20 ppm')
    if pre == 'J':
        n = re.search(r'1x0(\d)', fp)
        t = next((t for k, t in JTYPE if k in fp), 'Соединитель')
        return 'Соединитель', t.format(n=n.group(1) if n else '')
    if pre == 'SW':
        return 'Кнопка тактовая', '6 × 3,5 мм, SMD'
    if pre == 'JP':
        return 'Вилка штыревая 2 конт. 2,54 мм', value + ' (перемычку-джампер не ставить)'
    return KIND.get(pre, pre), value


def pins(fp):
    """Паяные точки: каждая медная площадка с номером. Не считаются: площадки только под пасту (без номера),
    переходные отверстия под корпусом (отверстие < 0,6 мм), неметаллизированные отверстия."""
    smd = tht = 0
    for p in findall(fp, 'pad'):
        layers = find(p, 'layers') or []
        if not p[1] or not any(l in ('F.Cu', '*.Cu') for l in layers[1:]):
            continue
        drill = find(p, 'drill')
        if p[2] == 'thru_hole' and drill:
            if float(drill[2] if drill[1] == 'oval' else drill[1]) >= 0.6:
                tht += 1
        elif p[2] == 'smd':
            smd += 1
    return smd, tht


def collect(board):
    notes = notes_by_lcsc()
    mount, dnp, other = defaultdict(list), defaultdict(list), defaultdict(list)
    info = {}
    for fp in findall(parse(Path(board).read_text(encoding='utf-8')), 'footprint'):
        p = {x[1]: x[2] for x in findall(fp, 'property')}
        ref, attr = p['Reference'], (find(fp, 'attr') or [])[1:]
        pre = re.match(r'[A-Z]+', ref).group()
        fpn = fp[1].split(':')[-1]
        l = p.get('LCSC', '').strip()
        mpn0, note = notes.get(l, ('', ''))
        mpn = (p.get('MPN') or mpn0 or '').split(' (')[0]
        if mpn.startswith('Molex 5566'):
            mpn = mpn0
        if mpn.startswith('CND-tek '):
            mpn = mpn[8:]
        if 'exclude_from_bom' in attr:
            other[(pre, fpn)].append(ref)
            continue
        key = (l or ref, pre if pre != 'F' or ref != 'F1' else 'F1')
        name, par = describe(pre, p.get('Value', ''), fpn, mpn, note, ref)
        smd, tht = pins(fp)
        if key in info and pre in ('J', 'SW'):
            info[key]['use'].append(f'{ref} — {p.get("Value", "")}')
        use = [f'{ref} — {p.get("Value", "")}'] if pre in ('J', 'SW', 'JP') else []
        if key in info:
            use = info[key]['use']
        info[key] = dict(use=use, name=name, par=par, fp=fpn, maker=maker(mpn, note), mpn=mpn, lcsc=l, smd=smd, tht=tht,
                         mount='выводной' if 'through_hole' in attr else 'SMD', pre=pre)
        (dnp if 'dnp' in attr else mount)[key].append(ref)
    return mount, dnp, other, info


def pnp(board, out):
    b = parse(Path(board).read_text(encoding='utf-8'))
    xs, ys = [], []
    for n in b:
        if isinstance(n, list) and n and n[0].startswith('gr_') and (find(n, 'layer') or [0, ''])[1] == 'Edge.Cuts':
            for k in ('start', 'end'):
                e = find(n, k)
                if e:
                    xs.append(float(e[1]))
                    ys.append(float(e[2]))
    x0, y0 = min(xs), max(ys)
    rows = []
    for fp in findall(b, 'footprint'):
        p = {x[1]: x[2] for x in findall(fp, 'property')}
        attr = (find(fp, 'attr') or [])[1:]
        if 'dnp' in attr or 'exclude_from_bom' in attr or 'exclude_from_pos_files' in attr:
            continue
        at = find(fp, 'at')
        rot = float(at[3]) % 360 if len(at) > 3 else 0.0
        rows.append((p['Reference'], p.get('Value', ''), fp[1].split(':')[-1], float(at[1]) - x0, y0 - float(at[2]), rot,
                     'TOP' if find(fp, 'layer')[1] == 'F.Cu' else 'BOTTOM', 'THT' if 'through_hole' in attr else 'SMD'))
    with open(out, 'w', encoding='utf-8-sig', newline='') as f:
        f.write('Designator;Value;Footprint;X_mm;Y_mm;Rotation;Side;Type\n')
        for r in sorted(rows, key=lambda r: nat(r[0])):
            f.write(f'{r[0]};{r[1]};{r[2]};{r[3]:.3f};{r[4]:.3f};{r[5]:.1f};{r[6]};{r[7]}\n')
    print(f'{out}: {len(rows)} деталей, начало — левый нижний угол платы')


def main(board, out, pnp_out=None):
    if pnp_out:
        pnp(board, pnp_out)
    mount, dnp, other, info = collect(board)
    wb = Workbook()
    ws = wb.active
    ws.title = 'Спецификация'
    thin = Side(style='thin', color='999999')
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    head = PatternFill('solid', fgColor='DDE4EE')
    wrap = Alignment(wrap_text=True, vertical='top')
    cols = ['№', 'Позиционные обозначения', 'Кол-во на 1 плату', 'Наименование', 'Номинал / параметры',
            'Корпус (посадочное место KiCad)', 'Производитель', 'Парт-номер (MPN)', 'Код LCSC', 'Монтаж',
            'Паек SMD на 1 плату', 'Паек выводных на 1 плату', 'Замена']
    widths = [5, 34, 9, 30, 34, 34, 15, 27, 11, 10, 10, 10, 26]
    ws.append([f'{TITLE}, ред. {REV} — спецификация компонентов для монтажа'])
    ws.append([f'Автор: {AUTHOR}. Дата: {date.today():%d.%m.%Y}. Плата 240 × 127 мм, 4 слоя, монтаж с одной стороны (верх).'])
    ws.append([])
    ws.append(cols)
    hr = ws.max_row
    for c in ws[hr]:
        c.font, c.fill, c.border, c.alignment = Font(bold=True), head, box, Alignment(wrap_text=True, vertical='center')
    order = ['U', 'Q', 'D', 'T', 'Y', 'L', 'FB', 'F1', 'F', 'C', 'R', 'J', 'JP', 'SW', 'BT']
    keys = sorted(mount, key=lambda k: (order.index(k[1]) if k[1] in order else 99, nat(sorted(mount[k], key=nat)[0])))
    tot = dict(n=0, smd=0, tht=0, lines=0)
    for i, k in enumerate(keys, 1):
        d, refs = info[k], mount[k]
        n = len(refs)
        passive = (d['pre'] in ('R', 'C') and not d['fp'].startswith('CP_')) or d['lcsc'] in ('C2286', 'C1017', 'C81598')
        repl = 'аналог с теми же параметрами допускается' if passive else ('по согласованию' if d['pre'] in ('D', 'F', 'L', 'FB', 'J', 'SW', 'BT', 'JP') else 'нет')
        par = d['par'] + ('\n' + '\n'.join(sorted(d['use'], key=lambda u: nat(u.split(' ')[0]))) if d['use'] else '')
        ws.append([i, refs_text(refs), n, d['name'], par, d['fp'], d['maker'], d['mpn'], d['lcsc'], d['mount'],
                   d['smd'] * n, d['tht'] * n, repl])
        tot['n'] += n
        tot['smd'] += d['smd'] * n
        tot['tht'] += d['tht'] * n
        tot['lines'] += 1
    first, last = hr + 1, ws.max_row
    ws.append(['', 'ИТОГО на 1 плату', tot['n'], f'{tot["lines"]} позиций', '', '', '', '', '', '', tot['smd'], tot['tht'], ''])
    for row in ws.iter_rows(min_row=first, max_row=ws.max_row):
        for c in row:
            c.border, c.alignment = box, wrap
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    ws.append([])
    for t in ['Примечания:',
              '1. Монтаж только на верхней стороне платы. Нижняя сторона — без компонентов.',
              '2. F1 — устанавливается только держатель Keystone 3568-10; вставку предохранителя 7,5 А не устанавливать (ставит заказчик).',
              '3. JP1 — запаять вилку; перемычку-джампер не устанавливать.',
              '4. Компоненты с листа «Не устанавливать» не паять, площадки оставить свободными.',
              '5. Ключи и полярность — по сборочному чертежу (вывод 1 ИМС, катод диодов, «+» электролитических конденсаторов).',
              '6. Замена ИМС, транзисторов, разъёмов — только по согласованию с заказчиком; при отсутствии позиции просьба сообщить.',
              '7. Координаты установки — файл pnp_mso74.csv (мм, начало — левый нижний угол платы, ось Y вверх, поворот против часовой).']:
        ws.append([t])
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=hr, column=i).column_letter].width = w
    ws['A1'].font = Font(bold=True, size=13)
    ws.freeze_panes = ws.cell(row=hr + 1, column=1)
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f'{hr}:{hr}'

    ws2 = wb.create_sheet('Не устанавливать')
    ws2.append(['Не устанавливать (площадки оставить свободными)'])
    ws2.append(['Позиционные обозначения', 'Кол-во', 'Что это', 'Примечание'])
    for c in ws2[2]:
        c.font, c.fill, c.border = Font(bold=True), head, box
    for k in sorted(dnp, key=lambda k: nat(dnp[k][0])):
        d = info[k]
        ws2.append([refs_text(dnp[k]), len(dnp[k]), f'{d["name"]} {d["par"]}', 'DNP — резерв на будущее, не паять'])
    for (pre, fpn), refs in sorted(other.items()):
        what = {'TP': 'Контрольные площадки (без компонента)', 'H': 'Крепёжные отверстия M3'}.get(pre, fpn)
        ws2.append([refs_text(refs), len(refs), what, 'не компонент, монтажа нет'])
    for row in ws2.iter_rows(min_row=3, max_row=ws2.max_row):
        for c in row:
            c.border, c.alignment = box, wrap
    for col, w in zip('ABCD', (30, 9, 50, 36)):
        ws2.column_dimensions[col].width = w
    ws2['A1'].font = Font(bold=True, size=13)
    wb.save(out)
    print(f'{out}: позиций {tot["lines"]}, деталей {tot["n"]}, паек SMD {tot["smd"]}, выводных {tot["tht"]}; '
          f'DNP {sum(map(len, dnp.values()))}, не компоненты {sum(map(len, other.values()))}')


if __name__ == '__main__':
    main(*sys.argv[1:4])
