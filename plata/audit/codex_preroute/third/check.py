"""Дополнительные проверки третьего захода (KiCad 9 pcbnew).

Сначала ../check.py: повторяемость, fixed DSN и roundtrip через пустой SES.
Затем этот файл: --board BOARD --drc DRC.json --dsn power.dsn
--baseline ../drc.json --base-verification base-verification.json --output verification.json
"""
import argparse
import collections
import json
from pathlib import Path
import re
import sys

import pcbnew
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'kicad/gen'))
from sexp import parse,find,findall


def unconnected_by_net(drc):
    counts=collections.Counter()
    for item in drc['unconnected_items']:
        names=set()
        for endpoint in item['items']:
            names.update(re.findall(r'\[([^\]]+)\]',endpoint['description']))
        for name in names:counts[name]+=1
    return counts


def main():
    ap=argparse.ArgumentParser()
    for name in ('board','drc','dsn','baseline','base-verification','output'):ap.add_argument('--'+name,required=True)
    a=ap.parse_args();b=pcbnew.LoadBoard(a.board)
    manifest=json.loads(Path(a.board).with_suffix('.preroute.json').read_text(encoding='utf-8'))
    assert not manifest['not_routed']
    assert all(not c['unconnected'] for c in manifest['supply_checks'].values())
    drc=json.loads(Path(a.drc).read_text());baseline=json.loads(Path(a.baseline).read_text())
    types=collections.Counter(v['type'] for v in drc['violations'])
    for violation in drc['violations']:
        if violation['type'].startswith('silk'):continue
        assert violation['type']=='hole_clearance',violation
        assert any('J5' in i['description'] for i in violation['items']),violation
    assert types['hole_clearance']==4
    remaining=unconnected_by_net(drc);before=unconnected_by_net(baseline)
    supplies=set(manifest['supply_checks'])
    assert all(remaining[n]==0 for n in supplies),'native DRC: питание не соединено'
    regressions={n:(before[n],count) for n,count in remaining.items() if n not in supplies and count>before[n]}
    assert not regressions,regressions
    named={z.GetZoneName():z for z in b.Zones()}
    priorities={suffix:named['MSO74_PREROUTE_V1:'+suffix].GetAssignedPriority()
                for suffix in ('U1:VIN','Q1-U1:VIN-top','Q1:drain')}
    assert len(set(priorities.values()))==3,priorities
    guard=named['MSO74_PREROUTE_V1:right-edge-guard']
    assert guard.IsLocked() and guard.GetIsRuleArea() and guard.GetDoNotAllowTracks() and guard.GetDoNotAllowVias()
    assert all(z.IsLocked() for name,z in named.items() if name.startswith('MSO74_PREROUTE_V1:'))
    dsn=parse('\n'.join(l for l in Path(a.dsn).read_text().splitlines() if 'string_quote' not in l))
    structure=find(dsn,'structure');guard_layers=[]
    for keepout in findall(structure,'keepout'):
        polygon=find(keepout,'polygon')
        if not polygon:continue
        coords=list(map(float,polygon[3:]))
        if coords and min(coords[::2])==269650 and max(coords[::2])==270000:guard_layers.append(polygon[1])
    assert set(guard_layers)=={'F.Cu','B.Cu','In1.Cu','In2.Cu'},guard_layers
    vias={t.m_Uuid.AsString():t for t in b.GetTracks() if isinstance(t,pcbnew.PCB_VIA)}
    main_planes={}
    for net in ('+3V3','+24V_P'):
        shapes=[]
        for z in b.Zones():
            if z.GetNetname()!=net or not z.IsOnLayer(pcbnew.In2_Cu) or z.GetIsRuleArea():continue
            poly=z.GetFilledPolysList(pcbnew.In2_Cu)
            for i in range(poly.OutlineCount()):
                part=pcbnew.SHAPE_POLY_SET();part.AddOutline(poly.COutline(i))
                for j in range(poly.HoleCount(i)):part.AddHole(poly.CHole(i,j))
                shapes.append(part)
        main_planes[net]=max(shapes,key=lambda p:abs(p.COutline(0).Area()))
    added=collections.Counter();plane=collections.Counter()
    for entry in manifest['supply_added_vias']:
        v=vias[entry['uuid']];net=v.GetNetname();added[net]+=1
        assert v.IsLocked() and entry['source_connected']
        hole=pcbnew.SHAPE_CIRCLE(v.GetPosition(),v.GetDrill()//2)
        for f in b.GetFootprints():
            for pad in f.Pads():
                if pad.GetDrillSize().x or not pad.IsOnLayer(pcbnew.F_Cu):continue
                assert not pad.GetEffectiveShape(pcbnew.F_Cu).Collide(hole,100000),('via hole near SMD',entry,f.GetReference(),pad.GetNumber())
        assert (v.GetWidth(pcbnew.F_Cu),v.GetDrill()) in ((600000,300000),(450000,200000))
        contact=net in main_planes and main_planes[net].Collide(v.GetEffectiveShape(pcbnew.In2_Cu),2)
        assert bool(contact)==entry['main_plane_connected']
        if contact:plane[net]+=1
    result=json.loads(Path(a.base_verification).read_text())
    result.update({'supplies':manifest['supply_checks'],'new_supply_vias':dict(sorted(added.items())),
                   'new_main_plane_vias':dict(sorted(plane.items())),'new_main_plane_vias_total':sum(plane.values()),
                   'native_DRC_violations':dict(types),'native_unconnected_items':len(drc['unconnected_items']),
                   'native_unconnected_supply_items':{n:remaining[n] for n in sorted(supplies)},
                   'other_net_unconnected_regressions':regressions,'VIN_B_priorities':priorities,
                   'new_supply_holes_clear_of_SMD_by_mm':0.1,
                   'right_edge_keepout_in_DSN':sorted(guard_layers)})
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
