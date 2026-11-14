#!/usr/bin/env python3
# UTF-8. No changes to schematic, PCB or source generators.
from pathlib import Path
import json,math,sys,xml.etree.ElementTree as ET,collections,csv,re
import argparse
a=argparse.ArgumentParser(description='Compare KiCad XML, netlist, PCB and placement; run against pinned source/export directories.')
a.add_argument('--repo',type=Path,required=True);a.add_argument('--ci',type=Path,required=True);a.add_argument('--old-ci',type=Path,required=True);a.add_argument('--out',type=Path,required=True);args=a.parse_args()
r=args.repo;ci=args.ci;old=args.old_ci;result_dir=args.out;result_dir.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(r/'plata/kicad/gen'));from sexp import parse,find,findall

def read(folder):
 x=ET.parse(folder/'mso74-plata.xml').getroot();cs={}
 for c in x.findall('components/comp'):cs[c.get('ref')]={'value':c.findtext('value'),'footprint':c.findtext('footprint'),'fields':{f.get('name'):f.text for f in c.findall('fields/field')},'lib':c.find('libsource').attrib,'pins':{}}
 for n in x.findall('nets/net'):
  for v in n.findall('node'):cs[v.get('ref')]['pins'][v.get('pin')]={'net':n.get('name'),'function':v.get('pinfunction')}
 # Independently check .net equals XML
 t=parse((folder/'mso74-plata.net').read_text());ns={str(find(n,'name')[1]).replace('{slash}','/'):set((str(find(v,'ref')[1]),str(find(v,'pin')[1])) for v in findall(n,'node')) for n in findall(find(t,'nets'),'net')};xs={n.get('name'):set((v.get('ref'),v.get('pin'))for v in n.findall('node'))for n in x.findall('nets/net')};assert ns==xs
 return cs
new=read(ci);before=read(old);changed={}
# Ignore unconnected net names; compare connected endpoint identity as well as net names.
for ref in sorted(set(new)&set(before)):
 a,b=before[ref],new[ref];d={}
 for f in ['value','footprint','fields','lib','pins']:
  if a[f]!=b[f]:d[f]={'before':a[f],'after':b[f]}
 if d:changed[ref]=d
pcb=parse((ci/'mso74-plata.kicad_pcb').read_text());fps={};pads={};centers={}
for fp in findall(pcb,'footprint'):
 ref=next(str(x[2]) for x in findall(fp,'property') if str(x[1])=='Reference');fps[ref]=fp;at=find(fp,'at');x,y=float(at[1]),float(at[2]);rot=float(at[3]) if len(at)>3 else 0;centers[ref]=[x,y,rot];pads[ref]={}
 for pad in findall(fp,'pad'):
  a=find(pad,'at');u,v=float(a[1]),float(a[2]);q=math.radians(-rot);ax=x+u*math.cos(q)-v*math.sin(q);ay=y+u*math.sin(q)+v*math.cos(q);nt=find(pad,'net');size=find(pad,'size');pads[ref].setdefault(str(pad[1]),[]).append({'xy':[ax,ay],'net':str(nt[-1]) if nt else '', 'size':size[1:],'type':str(pad[2]),'drill':find(pad,'drill')[1:] if find(pad,'drill') else None})
place=json.loads((r/'plata/kicad/placement.json').read_text())['parts'];mismatch=[k for k,v in place.items() if any(abs(a-b)>1e-6 for a,b in zip([v[0]+30,v[1]+30,v[2]],centers.get(k,[-999]*3)))]
cells={'U2':{'cin':['C6','C7'],'L':['L1'],'cout':['C9','C10','C11'],'fb':['R13','R14']},'U3':{'cin':['C12','C13'],'L':['L2'],'cout':['C15','C16','C17'],'fb':['R18','R19']},'U4':{'cin':['C18','C19'],'L':['L3'],'cout':['C21','C22','C23'],'fb':['R23','R24']},'U5':{'cin':['C24','C25','C26','C27','C110'],'L':['L4'],'cout':['C30','C31','C32','C33','C34'],'fb':['R30','R31']},'U6':{'cin':['C35','C36','C37','C38','C111'],'L':['L5'],'cout':['C41','C42','C43','C44','C45'],'fb':['R37','R38']}}
dist={u:{g:{v:round(math.dist(place[u][:2],place[v][:2]),3)for v in vs}for g,vs in d.items()}for u,d in cells.items()}
def expand_refs(text):
 out=[]
 for x in text.split(','):
  x=x.strip();m=re.fullmatch(r'([A-Za-z]+)(\d+)-([A-Za-z]+)?(\d+)',x)
  if m:
   assert m[3] in [None,m[1]];out.extend(m[1]+str(k)for k in range(int(m[2]),int(m[4])+1))
  elif x:out.append(x)
 return out
bs={};
for f in ['bom.csv','bom_full.csv']:
 rows=list(csv.DictReader((ci/f).open()));bs[f]={'rows':len(rows),'references':sorted(x for row in rows for x in row['Reference'].split(',')),'fields':list(rows[0]),'expanded_references':sorted(x for row in rows for x in expand_refs(row['Reference']))}
checks=[]
for ref,c in new.items():
 for pin,n in c['pins'].items():
  if n['net'].startswith('unconnected-'):continue
  actual=pads.get(ref,{}).get(pin,[])
  if not actual or any(a['net']!=n['net'] for a in actual):checks.append([ref,pin,n,actual])
res={'components_old':len(before),'components_new':len(new),'added':sorted(set(new)-set(before)),'removed':sorted(set(before)-set(new)),'changed':changed,'centers':centers,'pads':pads,'distances_center_mm':dist,'placement_pcb_mismatches':mismatch,'netlist_pcb_mismatches':checks,'bom':bs,'drc':dict(collections.Counter(__import__('re').findall(r'^\[([^\]]+)\]',(ci/'drc.rpt').read_text(),__import__('re').M))),'tracks':len(findall(pcb,'segment')),'vias':len(findall(pcb,'via')),'zones':len(findall(pcb,'zone'))}
(result_dir/'verification.json').write_text(json.dumps(res,ensure_ascii=False,indent=2));(result_dir/'inventory.json').write_text(json.dumps(new,ensure_ascii=False,indent=2));print('added',res['added'],'removed',res['removed']);print('changes',[(k,list(v))for k,v in changed.items()]);print('distances',json.dumps(dist,ensure_ascii=False));print('BOM',[(k,v['rows'],len(v['references']))for k,v in bs.items()]);print('mismatches',len(checks),len(mismatch));print('DRC',res['drc']);
for ref in ['Q5','Q6','Q7','Q8','Q9','U23','D48','D49','R115','R116','R117','R118','C110','C111','C112','C114','T1','T2']+[f'TP{i}'for i in range(1,22)]:print(ref,new[ref]['value'],new[ref]['pins'],centers[ref])
