"""Проверка финальной меди. Запуск системным Python с pcbnew 9.
verify.py SOURCE.kicad_pcb FINAL.kicad_pcb REPEAT.kicad_pcb NETLIST.net
Результат JSON в stdout; исходные файлы не меняются.
"""
from pathlib import Path
import sys,json,hashlib,collections,fnmatch
import pcbnew
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'kicad/gen'))
import pcb_preroute as p,pcb_rules,netlist
root=Path(__file__).resolve().parent
source,final,repeat,netfile=map(Path,sys.argv[1:])
a,b,c=[pcbnew.LoadBoard(str(f)) for f in (source,final,repeat)]
m=json.loads((root/'changes.json').read_text());d=json.loads((root/'drc.json').read_text())
def coord(q):return q.x,q.y
def geom(t):
    if isinstance(t,pcbnew.PCB_VIA):
        return ('via',t.GetNetname(),coord(t.GetPosition()),t.GetWidth(pcbnew.F_Cu),t.GetDrillValue(),t.TopLayer(),t.BottomLayer(),t.IsLocked())
    return ('track',t.GetNetname(),coord(t.GetStart()),coord(t.GetEnd()),t.GetWidth(),t.GetLayer(),t.IsLocked())
def copper(board):
    tracks=sorted(geom(t) for t in board.GetTracks())
    zones=[]
    def chain(ch):return [coord(ch.CPoint(i)) for i in range(ch.PointCount())]
    for z in board.Zones():
        parts=[]
        for layer in (pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu):
            if not z.IsOnLayer(layer):continue
            poly=z.GetFilledPolysList(layer)
            parts.append((layer,[(chain(poly.COutline(i)),[chain(poly.CHole(i,j)) for j in range(poly.HoleCount(i))]) for i in range(poly.OutlineCount())]))
        zones.append((z.GetNetname(),z.GetZoneName(),z.GetAssignedPriority(),z.IsLocked(),parts))
    return hashlib.sha256(json.dumps((tracks,sorted(zones)),ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def footprints(board):
    result={}
    for f in board.GetFootprints():
        pads=[]
        for pad in f.Pads():
            pads.append((pad.m_Uuid.AsString(),pad.GetNumber(),pad.GetNetname(),coord(pad.GetPosition()),coord(pad.GetSize()),coord(pad.GetDrillSize()),pad.GetOrientationDegrees(),pad.GetShape(),pad.GetAttribute(),str(pad.GetLayerSet().FmtHex())))
        result[f.GetReference()]=(f.m_Uuid.AsString(),str(f.GetFPID().GetUniStringLibId()),coord(f.GetPosition()),f.GetOrientationDegrees(),sorted(pads))
    return result
old={t.m_Uuid.AsString():t for t in a.GetTracks()};new={t.m_Uuid.AsString():t for t in b.GetTracks()}
removed=set(old)-set(new);added=set(new)-set(old)
expected_removed={x['uuid'] for x in m['removed'] if x['kind']!='zone'}
expected_added={x['uuid'] for x in m['added']}
changed=[u for u in set(old)&set(new) if geom(old[u])!=geom(new[u])]
sense='bb2a6ca2-1fe2-47c4-896d-4805b344bf7d'
checks={
 'removed_tracks_match_manifest':removed==expected_removed,
 'new_tracks_match_manifest':added==expected_added,
 'only_existing_via_size_changed':changed==[sense],
 'sense_via_change_only_size_drill':geom(old[sense])[:3]+geom(old[sense])[5:]==geom(new[sense])[:3]+geom(new[sense])[5:],
 'footprints_positions_pads_nets_unchanged':footprints(a)==footprints(b),
 'all_added_copper_locked':all(new[u].IsLocked() for u in added),
 'minimum_added_track_015':all(t.GetWidth()>=p.mm(.15) for u,t in new.items() if u in added and not isinstance(t,pcbnew.PCB_VIA)),
 'new_via_sizes':all((t.GetWidth(pcbnew.F_Cu),t.GetDrillValue()) in ((p.mm(.45),p.mm(.2)),(p.mm(.6),p.mm(.3))) for u,t in new.items() if u in added and isinstance(t,pcbnew.PCB_VIA)),
 'In1_no_tracks':not any(not isinstance(t,pcbnew.PCB_VIA) and t.GetLayer()==pcbnew.In1_Cu for t in b.GetTracks()),
 'repeat_same_copper':copper(b)==copper(c),
 'DRC_909':d['kicad_version']=='9.0.9',
 'zero_unconnected':len(d['unconnected_items'])==0,
 'only_known_DRC':all(v['type'] in ('hole_clearance','silk_overlap','silk_over_copper','silk_edge_clearance') for v in d['violations']),
 'four_known_J5_holes':len([v for v in d['violations'] if v['type']=='hole_clearance'])==4 and all(all('J5' in i['description'] for i in v['items']) for v in d['violations'] if v['type']=='hole_clearance'),
}
fast=lambda t:any(cl in ('ETH','USB') and fnmatch.fnmatchcase(t.GetNetname(),pat) for cl,pat in pcb_rules.PATTERNS)
checks['all_original_ETH_USB_copper_unchanged']=all(u in new and geom(t)==geom(new[u]) for u,t in old.items() if fast(t))
fast_b=[t for t in b.GetTracks() if fast(t) and not isinstance(t,pcbnew.PCB_VIA) and t.GetLayer()==p.B]
cuts=[]
for u in added:
    t=new[u]
    if not t.IsOnLayer(pcbnew.In2_Cu):continue
    for f in fast_b:
        if pcbnew.SHAPE.Collide(t.GetEffectiveShape(pcbnew.In2_Cu),f.GetEffectiveShape(p.B),p.mm(.3)):
            cuts.append((u,t.GetNetname(),f.GetNetname()))
checks['new_In2_no_direct_cut_B_fast_reference']=not cuts
comps,nets=netlist.read(str(netfile));fp={f.GetReference():f for f in b.GetFootprints()};parity=[]
for ref,comp in comps.items():
    if ref not in fp:parity.append((ref,'missing'));continue
    pads=collections.defaultdict(list)
    for pad in fp[ref].Pads():pads[pad.GetNumber()].append(pad.GetNetname())
    for pin,net in comp.pins.items():
        # pcb_build намеренно не назначает net KiCad no-connect выводам.
        if net.startswith('unconnected-'):net=''
        if pin not in pads or any(n!=net for n in pads[pin]):parity.append((ref,pin,net,pads.get(pin)))
checks['netlist_pin_parity']=not parity
checks['U1_EP_15_PTH_preserved']=sum(pad.GetNumber()=='21' and bool(pad.GetDrillSize().x) for pad in fp['U1'].Pads())==15
counts=collections.Counter(v['type'] for v in d['violations'])
result={'checks':checks,'failed':[k for k,v in checks.items() if not v],
 'copper_sha256':copper(b),'DRC':{'version':d['kicad_version'],'unconnected':len(d['unconnected_items']),'violations':dict(counts)},
 'source_tracks_vias':len(old),'final_tracks_vias':len(new),'retained':len(set(old)&set(new)),
 'removed_tracks_vias':len(removed),'added_tracks_vias':len(added),'changed_existing':changed,
 'added_counts':dict(collections.Counter('via' if isinstance(new[u],pcbnew.PCB_VIA) else 'track' for u in added)),
 'removed_by_net':dict(collections.Counter(old[u].GetNetname() for u in removed)),
 'footprints':len(fp),'netlist_components':len(comps),'parity_errors':parity,'reference_cuts':cuts,
 'file_sha256':hashlib.sha256(final.read_bytes()).hexdigest()}
print(json.dumps(result,ensure_ascii=False,indent=2))
if result['failed']:sys.exit(1)
