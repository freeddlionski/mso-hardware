#!/usr/bin/env python3
"""Воспроизводимые статические проверки аудита Codex 929198e.

Из корня репозитория:
  python plata/audit/codex_929198e/audit_checks.py \
    --ci-out /путь/к/ci_out --output /tmp/codex-verification.json \
    --plot /tmp/input_cap_distances.svg

ci_out — выгрузка из присланного архива или ветки kicad-out того же коммита.
Скрипт читает проект; изменяет только явно заданные --output и --plot.
Для SVG нужен matplotlib; для остальных проверок — только стандартная
библиотека Python и существующий plata/kicad/gen/sexp.py. Производственные
допуски, температуры и параметры ИС — входные данные из источников отчёта,
а не измерения. Аналоговое моделирование, ERC и DRC не запускаются.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import re
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_parser(repo):
    path = repo / 'plata/kicad/gen/sexp.py'
    spec = importlib.util.spec_from_file_location('project_sexp', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.parse, module.find, module.findall


def electrical(ci, pcb_path, repo):
    parse, find, findall = load_parser(repo)
    xml = ET.parse(ci / 'mso74-plata.xml').getroot()
    comps = {c.get('ref'): {'value': c.findtext('value'), 'pins': {}}
             for c in xml.findall('components/comp')}
    nets_xml = {}
    for net in xml.findall('nets/net'):
        name = net.get('name')
        nets_xml[name] = {(n.get('ref'), n.get('pin')) for n in net.findall('node')}
        for n in net.findall('node'):
            comps[n.get('ref')]['pins'][n.get('pin')] = name
    netlist = parse((ci / 'mso74-plata.net').read_text(encoding='utf-8'))
    nets_sexp = {}
    for net in findall(find(netlist, 'nets'), 'net'):
        name = str(find(net, 'name')[1]).replace('{slash}', '/')
        nets_sexp[name] = {(str(find(n, 'ref')[1]), str(find(n, 'pin')[1]))
                          for n in findall(net, 'node')}
    pcb = parse(pcb_path.read_text(encoding='utf-8'))
    footprints = {}
    for fp in findall(pcb, 'footprint'):
        ref = next((str(v[2]) for v in findall(fp, 'property')
                    if v[1] == 'Reference'), None)
        footprints[ref] = fp
    mismatches = []
    for ref, comp in comps.items():
        fp = footprints.get(ref)
        if fp is None:
            mismatches.append({'ref': ref, 'issue': 'missing footprint'})
            continue
        for number, net in comp['pins'].items():
            if net.startswith('unconnected-'):
                continue
            pads = [p for p in findall(fp, 'pad') if str(p[1]) == number]
            if not pads:
                mismatches.append({'ref': ref, 'pin': number, 'issue': 'missing pad'})
            for pad in pads:
                actual = find(pad, 'net')
                actual_name = str(actual[-1]) if actual else None
                if actual_name != net:
                    mismatches.append({'ref': ref, 'pin': number,
                                       'expected': net, 'actual': actual_name})
    pairs = {'U2': ['C6', 'C7'], 'U3': ['C12', 'C13'], 'U4': ['C18', 'C19'],
             'U5': ['C24', 'C25', 'C26', 'C27'],
             'U6': ['C35', 'C36', 'C37', 'C38']}
    points = {r: tuple(map(float, find(fp, 'at')[1:3]))
              for r, fp in footprints.items()}
    distances = {u: {c: round(math.dist(points[u], points[c]), 3) for c in caps}
                 for u, caps in pairs.items()}
    results = {
        'components': len(comps), 'nets': len(nets_xml),
        'net_and_xml_equal_after_escaping_normalization': nets_xml == nets_sexp,
        'unexpected_singletons': [n for n, nodes in nets_xml.items()
                                 if len(nodes) == 1 and not n.startswith('unconnected-')],
        'pcb_footprints': len(footprints),
        'pcb_tracks': len(findall(pcb, 'segment')),
        'pcb_vias': len(findall(pcb, 'via')),
        'pcb_zones': len(findall(pcb, 'zone')),
        'pcb_pad_mismatches': mismatches,
        'cin_distances_mm_center_to_center': distances,
        'drc_types_from_existing_report': dict(Counter(re.findall(
            r'^\[([^\]]+)\]', (ci / 'drc.rpt').read_text(encoding='utf-8'), re.M))),
    }
    return results, points, pairs


def calculations():
    rows = [('U2/L1', .6 * (1 + 100 / 5.23), 10e-6, .20, 500e3, 1.0),
            ('U3/L2', .6 * (1 + 100 / 13.7), 6.8e-6, .20, 500e3, 1.0),
            ('U4/L3', .6 * (1 + 100 / 22.1), 4.7e-6, .30, 500e3, 1.2),
            ('U5,U6/L4,L5', 1 * (1 + 100 / 24.9), 6.8e-6, .30, 400e3, 5.0)]
    converters = []
    for tag, vout, inductance, tolerance, frequency, load in rows:
        ripple24 = vout * (1 - vout / 24) / (inductance * frequency)
        ripple32 = vout * (1 - vout / 32) / (inductance * frequency)
        ripple_worst = vout * (1 - vout / 32) / (
            inductance * (1 - tolerance) * frequency * .9)
        converters.append({'tag': tag, 'vout_V': vout, 'L_H': inductance,
                           'L_initial_tolerance': tolerance, 'f_Hz': frequency,
                           'load_A': load, 'ripple24_A': ripple24,
                           'ripple32_A': ripple32,
                           'peak32_Lmin_fmin_A': load + ripple_worst / 2,
                           'irms24_A': math.sqrt(load**2 + ripple24**2 / 12)})
    thresholds = {}
    for mode in ['UVLO', 'OVP']:
        values = []
        for a, b, c, factor in itertools.product([.99, 1.01], repeat=4):
            r1, r2, r3 = 390e3 * a, 19.1e3 * b, 15e3 * c
            threshold = 1.2 * (1.02 if factor > 1 else .98)
            values.append(threshold * (r1 + r2 + r3) /
                          ((r2 + r3) if mode == 'UVLO' else r3))
        thresholds[mode] = {'min_V': min(values), 'max_V': max(values),
                            'note': '±1% резисторы, ±2% порог; без утечек входов'}
    return {'buck_CCM': converters, 'eFuse_thresholds': thresholds,
            'pca9555_default_buffer_input_typical_V': 3.3 * 100 / (100 + 100),
            'pca9555_with_10k_pulldown_typical_V': 3.3 * 10 / (100 + 10),
            'rs232_5V_3k_load_after_2k2_V': 5 * 3 / (3 + 2.2),
            'rs485_ac_termination': {'tau_s': 120 * 100e-9,
                                    'initial_current_at_32V_A': 32 / 120,
                                    'capacitor_energy_J': .5 * 100e-9 * 32**2},
            'dnp_fault_if_680ohm_fitted': {'B_resistor_W': 32**2 / 680,
                                         'A_resistor_W': (32 - 3.3)**2 / 680,
                                         'A_into_3V3_A': (32 - 3.3) / 680},
            'ptc_hold_A_at_70C_reference': {'2920L500/16': 2.90,
                                         '2920L110/60': .64,
                                         '2920L075/60': .44},
            'tdk_47u_typical_effective_4pcs_at_5V_F': 4 * 47e-6 * .65,
            'i2c_Cmax_F_for_300ns_4k7': 300e-9 / (.8473 * 4700)}


def plot(points, pairs, path):
    import os
    import tempfile
    os.environ.setdefault('MPLCONFIGDIR', tempfile.mkdtemp(prefix='codex-audit-mpl-'))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(13, 8))
    ax.add_patch(Rectangle((0, 0), 110, 120, fill=False, ec='black', lw=1))
    colors = ['#2c7fb8', '#41ab5d', '#756bb1', '#d7301f', '#e08214']
    for color, (u, caps) in zip(colors, pairs.items()):
        ux, uy = (x - 30 for x in points[u])
        ax.scatter(ux, uy, c=color, marker='s', s=90)
        ax.annotate(u, (ux, uy), xytext=(5, -14), textcoords='offset points', weight='bold')
        for c in caps:
            cx, cy = (x - 30 for x in points[c])
            ax.plot([ux, cx], [uy, cy], color=color, alpha=.45, lw=1)
            ax.scatter(cx, cy, c=color, marker='o', s=28)
            ax.annotate(c, (cx, cy), xytext=(3, 4), textcoords='offset points', fontsize=7)
        values = ', '.join(f'{c}: {math.dist(points[u], points[c]):.1f}' for c in caps)
        ax.plot([], [], color=color, label=f'{u} -> {values} mm')
    ax.set_xlim(-2, 112)
    ax.set_ylim(122, -2)
    ax.set_aspect('equal')
    ax.set_xlabel('X from board origin, mm')
    ax.set_ylabel('Y from board origin, mm')
    ax.set_title('929198e: buck input capacitors are remote from their ICs\n'
                 'C-001; positions from PCB; lines show distance, not routed traces')
    ax.grid(alpha=.15)
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=8)
    fig.tight_layout()
    fig.savefig(path, bbox_inches='tight')
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument('--ci-out', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--plot', type=Path)
    args = ap.parse_args()
    pcb = args.repo / 'plata/kicad/mso74-plata.kicad_pcb'
    if not pcb.exists():
        pcb = args.ci_out / 'mso74-plata.kicad_pcb'
    result, points, pairs = electrical(args.ci_out, pcb, args.repo)
    files = [args.ci_out / n for n in ['mso74-plata.net', 'mso74-plata.xml', 'drc.rpt']]
    files.append(pcb)
    result['input_sha256'] = {p.name: sha256(p) for p in files}
    result['audited_commit'] = '929198e4bce0ac9849e29535c30b98ebcf460e57'
    result['calculations'] = calculations()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.plot:
        plot(points, pairs, args.plot)
    print(json.dumps({'components': result['components'], 'nets': result['nets'],
                      'net_xml_match': result['net_and_xml_equal_after_escaping_normalization'],
                      'pad_mismatches': len(result['pcb_pad_mismatches']),
                      'output': str(args.output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
