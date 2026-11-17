"""Файлы заказа сборки JLCPCB из готовой платы.

python3 jlc_files.py BOARD.kicad_pcb POSITIONS.csv OUTDIR

OUTDIR/bom_jlc.csv — Comment, Designator, Footprint, LCSC Part # (одна строка на номер LCSC)
OUTDIR/cpl_jlc.csv — Designator, Mid X, Mid Y, Layer, Rotation (из kicad-cli pcb export pos)
OUTDIR/tht.txt    — выводные детали (их JLC паяет отдельно и дороже — решаем при заказе)
Детали без LCSC, с DNP или «не в BOM» (контрольные точки, отверстия) в заказ не идут.
Повороты — как у KiCad; JLC показывает превью, правка поворотов — на их шаге проверки.
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path
from sexp import parse, find, findall


def parts(board):
    out = {}
    for fp in findall(parse(Path(board).read_text(encoding='utf-8')), 'footprint'):
        props = {p[1]: p[2] for p in findall(fp, 'property')}
        attr = find(fp, 'attr') or []
        out[props['Reference']] = dict(
            value=props.get('Value', '') if props.get('Value', '').isascii() else (props.get('MPN') or props.get('LCSC', '')), lcsc=props.get('LCSC', '').strip(), fp=fp[1].split(':')[-1],
            skip='dnp' in attr or 'exclude_from_bom' in attr, tht='through_hole' in attr)
    return out


def main(board, pos, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    ps = parts(board)
    with open(pos, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    placed = {r['Ref'] for r in rows}
    groups = defaultdict(list)
    missing = []
    for ref, p in ps.items():
        if p['skip'] or ref not in placed:
            continue
        if not p['lcsc']:
            missing.append(ref)
            continue
        key = next((k for k in groups if k[0] == p['lcsc']), (p['lcsc'], p['value'], p['fp']))   # одна строка на номер LCSC
        groups[key].append(ref)
    key = lambda r: (''.join(c for c in r if c.isalpha()), int(''.join(c for c in r if c.isdigit()) or 0))
    with open(out / 'bom_jlc.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (lcsc, val, fp), refs in sorted(groups.items(), key=lambda g: key(sorted(g[1], key=key)[0])):
            w.writerow([val, ','.join(sorted(refs, key=key)), fp, lcsc])
    used = {r for refs in groups.values() for r in refs}
    with open(out / 'cpl_jlc.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for r in sorted(rows, key=lambda r: key(r['Ref'])):
            if r['Ref'] in used:
                w.writerow([r['Ref'], r['PosX'] + 'mm', r['PosY'] + 'mm',
                            'Top' if r['Side'].lower().startswith('top') else 'Bottom', r['Rot']])
    tht = sorted((r for r in used if ps[r]['tht']), key=key)
    (out / 'tht.txt').write_text('\n'.join(f"{r}\t{ps[r]['value']}\t{ps[r]['fp']}" for r in tht) + '\n', encoding='utf-8')
    print(f'BOM: {len(groups)} позиций, {len(used)} деталей (выводных {len(tht)}); без LCSC: {missing or "нет"}')


if __name__ == '__main__':
    main(*sys.argv[1:4])
