"""Сборка схемы: python3 build.py <путь к symbols из ветки kicad-libs>

Пишет plata/kicad/*.kicad_sch, lib/mso74.kicad_sym, lib/mso74.pretty, sym-lib-table, fp-lib-table и проект. Файлы схемы руками не правим — только здесь.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import custom_fps  # noqa: E402
import custom_syms  # noqa: E402
import kisch  # noqa: E402
import lcsc  # noqa: E402
import sheet_comm  # noqa: E402
import sheet_eth  # noqa: E402
import sheet_tp  # noqa: E402
import sheet_ext  # noqa: E402
import sheet_hub  # noqa: E402
import sheet_io  # noqa: E402
import sheet_mcu  # noqa: E402
import sheet_power  # noqa: E402

OUT = os.path.dirname(HERE)
POWER_NETS = ['GND', '+24V_P', '+12V', '+5V', '+3V3', '+3V3A', '+5V_LCD1', '+5V_LCD2']
PENDING = []   # межлистовые цепи, чей второй конец ещё не нарисован


def check_footprints(proj, official, own_fps):
    lst = os.path.join(os.path.dirname(official.rstrip('/')), 'footprints.txt')
    have = set(open(lst).read().split())
    bad = []
    for sh in proj.sheets:
        for p in sh.parts:
            fp = p.fp
            if not fp:
                from sexp import findall
                fp = next((str(x[2]) for x in findall(p.sym, 'property') if x[1] == 'Footprint'), '')
            if p.ref.startswith('#'):
                continue
            if not fp:
                bad.append('%s: нет посадочного места' % p.ref)
            elif not fp.startswith('mso74:') and fp not in have:
                bad.append('%s: нет %s' % (p.ref, fp))
    if bad:
        raise SystemExit('Посадочные места:\n' + '\n'.join(bad))
    # свои посадочные места обязаны лежать в lib/mso74.pretty (аудит 2, п. 16)
    nofp = sorted({p.ref + ' ' + p.fp for sh in proj.sheets for p in sh.parts
                   if p.fp.startswith('mso74:') and p.fp.split(':', 1)[1] not in own_fps})
    if nofp:
        raise SystemExit('Нет своих посадочных мест: ' + ', '.join(nofp))


def main(official):
    libdir = os.path.join(OUT, 'lib')
    os.makedirs(libdir, exist_ok=True)
    custom_syms.write(os.path.join(libdir, 'mso74.kicad_sym'))
    own_fps = custom_fps.write(libdir, os.path.join(os.path.dirname(official.rstrip('/')), 'footprints'))
    os.makedirs('/tmp/mso74lib', exist_ok=True)
    # mso74:X ищется как файл mso74.kicad_sym
    proj = kisch.Project([official, libdir], POWER_NETS)
    proj.pending = set(PENDING)
    sheet_power.build(proj)
    sheet_mcu.build(proj)
    sheet_eth.build(proj)
    sheet_comm.build(proj)
    sheet_io.build(proj)
    sheet_hub.build(proj)
    sheet_ext.build(proj)
    sheet_eth.switch(proj)        # последним: новые позиции получают новые номера, старые не сдвигаются
    proj.assign_late()            # исправления аудитов Codex/Kimi: новые позиции — в конец нумерации
    known = {n for sh in proj.sheets for p in sh.parts for n in p.nets.values() if n}
    sheet_tp.build(proj, known)
    check_footprints(proj, official, own_fps)
    missing = lcsc.apply(proj)
    if missing:
        print('ВНИМАНИЕ: нет номера LCSC у %d позиций:' % len(missing))
        for (v, fp), refs in sorted(missing.items()):
            print('  %-28s %-50s %s' % (v, fp, ' '.join(sorted(refs))))
    proj.write(OUT)
    with open(os.path.join(OUT, 'sym-lib-table'), 'w') as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "mso74")(type "KiCad")(uri "${KIPRJMOD}/lib/mso74.kicad_sym")(options "")(descr "Свои символы МСО74"))\n)\n')
    with open(os.path.join(OUT, 'fp-lib-table'), 'w') as f:
        f.write('(fp_lib_table\n  (version 7)\n  (lib (name "mso74")(type "KiCad")(uri "${KIPRJMOD}/lib/mso74.pretty")(options "")(descr "Свои посадочные места МСО74"))\n)\n')
    pro = os.path.join(OUT, kisch.PROJECT + '.kicad_pro')
    if not os.path.exists(pro):
        with open(pro, 'w') as f:
            json.dump({'meta': {'filename': kisch.PROJECT + '.kicad_pro', 'version': 3},
                       'schematic': {'drawing': {}, 'legacy_lib_dir': '', 'legacy_lib_list': []},
                       'sheets': [], 'text_variables': {}}, f, indent=2)
    print('ok:', [s.name for s in proj.sheets])


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/home/claude/kicad-libs/symbols')
