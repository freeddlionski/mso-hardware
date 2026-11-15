"""Проверка результата pcb_preroute.py (нужен /usr/bin/python3 с pcbnew).

python3 check.py --board final.kicad_pcb --again again.kicad_pcb \
  --roundtrip roundtrip.kicad_pcb --dsn power.dsn --output verification.json
Общие неразведённые связи проверяются отдельно kicad-cli pcb drc.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import sys

import pcbnew
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'kicad/gen'))
from sexp import parse,find,findall


def ring(chain):
    pts=[(chain.CPoint(i).x,chain.CPoint(i).y) for i in range(chain.PointCount())]
    if pts and pts[0]==pts[-1]:pts.pop()
    if not pts:return ()
    def normalized(v):
        i=min(range(len(v)),key=lambda i:v[i]);return tuple(v[i:]+v[:i])
    return min(normalized(pts),normalized(list(reversed(pts))))


def polygons(poly):
    return sorted((ring(poly.COutline(i)),tuple(sorted(ring(poly.CHole(i,j)) for j in range(poly.HoleCount(i)))))
                  for i in range(poly.OutlineCount()))


def signature(b):
    tracks=[]
    for t in b.GetTracks():
        assert t.IsLocked(),'незакреплённый track/via'
        if isinstance(t,pcbnew.PCB_VIA):
            tracks.append(('via',t.GetNetname(),t.GetPosition().x,t.GetPosition().y,t.GetWidth(pcbnew.F_Cu),t.GetDrill()))
        else:
            assert t.GetWidth()>=pcbnew.FromMM(.15),'дорожка тоньше .15'
            ends=sorted(((t.GetStart().x,t.GetStart().y),(t.GetEnd().x,t.GetEnd().y)))
            tracks.append(('track',t.GetNetname(),t.GetLayer(),t.GetWidth(),*ends))
    zones=sorted((z.GetNetname(),z.GetLayer(),z.GetZoneName(),z.GetAssignedPriority(),polygons(z.Outline()),
                  polygons(z.GetFilledPolysList(z.GetLayer()))) for z in b.Zones() if z.IsLocked() and not z.GetIsRuleArea())
    return sorted(tracks),zones


def main():
    ap=argparse.ArgumentParser()
    for n in ('board','again','roundtrip','dsn','output'):ap.add_argument('--'+n,required=True)
    a=ap.parse_args();b=pcbnew.LoadBoard(a.board);sig=signature(b)
    assert sig==signature(pcbnew.LoadBoard(a.again)),'недетерминированная геометрия'
    after=signature(pcbnew.LoadBoard(a.roundtrip))
    assert sig[0]==after[0],'SES изменил закреплённые tracks/vias'
    # Lock зоны фиксирует её границу. Import обязан заново залить зоны
    # вокруг новых дорожек, поэтому заполненные контуры не являются lock.
    assert [z[:5] for z in sig[1]]==[z[:5] for z in after[1]],'SES изменил границы закреплённых зон'
    refill_changed=[x[2] for x,y in zip(sig[1],after[1]) if x[5]!=y[5]]
    fp={f.GetReference():f for f in b.GetFootprints()}
    pth=[p for p in fp['U1'].Pads() if p.GetNumber()=='21' and p.GetDrillSize().x>0]
    assert len(pth)==15,'изменились PTH EP U1'
    center=fp['U22'].GetPosition()
    thermal=[t for t in b.GetTracks() if isinstance(t,pcbnew.PCB_VIA) and t.GetNetname()=='GND'
             and abs(t.GetPosition().x-center.x)<=pcbnew.FromMM(1.01)
             and abs(t.GetPosition().y-center.y)<=pcbnew.FromMM(1.01)]
    assert len(thermal)==9,'нет массива 3x3 под U22'
    for ref in ('U5','U6'):
        sw=next(p for p in fp[ref].Pads() if p.GetNumber()=='10')
        assert not any(t.GetNetname()=='GND' and isinstance(t,pcbnew.PCB_VIA)
                       and sw.GetEffectiveShape(pcbnew.F_Cu).Collide(t.GetEffectiveShape(pcbnew.F_Cu),0)
                       for t in b.GetTracks()),'GND via в SW LM61460'
    s='\n'.join(l for l in Path(a.dsn).read_text().splitlines() if 'string_quote' not in l)
    d=parse(s);w=find(d,'wiring');nets=find(d,'network');lib=find(d,'library');structure=find(d,'structure')
    wires=findall(w,'wire');vias=findall(w,'via')
    assert wires and all(find(t,'type')==['type','fix'] for t in wires+vias),'не fixed в DSN'
    assert any(p[1]=='Via[0-3]_450:200_um' for p in findall(lib,'padstack'))
    for c in findall(nets,'class'):
        if c[1] in ('ETH','USB'):
            assert find(find(c,'circuit'),'use_via')[1]=='Via[0-3]_450:200_um'
    planes=findall(structure,'plane')
    assert any(find(p,'polygon')[1]=='F.Cu' for p in planes),'нет закреплённой меди F в DSN'
    manifest=json.loads(Path(a.board).with_suffix('.preroute.json').read_text())
    assert not manifest['not_routed'],'незавершённая предразводка'
    eth=[p for p in manifest['pairs'] if p['name'].startswith('ETH ')]
    assert len(eth)==11 and len({p['name'] for p in eth})==11,'не все 11 Ethernet-пар'
    for pair in eth:
        for section in [pair]+([pair['preceding_section']] if 'preceding_section' in pair else []):
            assert max(v for fan in section['unpaired_fanout_lengths_mm'] for v in fan)<=3.0001,'fanout длиннее 3 мм'
    for ref,at in {'U10':(196,22),'U22':(206,44),'J7':(222.74,22),'J18':(222.74,45)}.items():
        p=fp[ref].GetPosition();assert math.dist((p.x/1e6-30,p.y/1e6-30),at)<.00001,'смещён центр '+ref
    by_id={t.m_Uuid.AsString():t for t in b.GetTracks()}
    for route in manifest['routes']:
        actual=sum(by_id[u].GetLength()/1e6 for u in route['item_uuids'])
        assert abs(actual-route['length_mm'])<.0001,'не совпала длина '+route['label']
    for pair in manifest['pairs']:assert pair['skew_mm']<=.5
    edge_max={}
    for edge in ('top','bottom','left','right'):
        pts=[v['at_mm'] for v in manifest['edge_stitches'] if v['edge']==edge]
        edge_max[edge]=max(math.dist(p,q) for p,q in zip(pts,pts[1:]))
        assert edge_max[edge]<=10,'слишком редкая сшивка '+edge
    result={'kicad':pcbnew.Version(),'deterministic_geometry':True,'empty_SES_preserves_tracks_vias_zone_outlines':True,'roundtrip_refill_changed_zones':refill_changed,
            'copper_sha256':hashlib.sha256(json.dumps(sig,ensure_ascii=False).encode()).hexdigest(),
            'tracks':sum(not isinstance(t,pcbnew.PCB_VIA) for t in b.GetTracks()),
            'vias':sum(isinstance(t,pcbnew.PCB_VIA) for t in b.GetTracks()),'locked_zones':len(sig[1]),
            'dsn_fixed_wires':len(wires),'dsn_fixed_vias':len(vias),'dsn_planes':len(planes),
            'ethernet_pairs':len(eth),'max_ethernet_skew_mm':max(p['skew_mm'] for p in eth),'edge_max_spacing_mm':edge_max,'U1_EP_PTH':len(pth),'U22_EP_vias':len(thermal),'unfinished':manifest['not_routed']}
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
