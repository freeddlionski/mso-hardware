#!/usr/bin/env python3
"""Run: python3 plata/audit/pass5/net_audit.py ../mso74-plata.xml"""
import csv,sys,pathlib,collections,xml.etree.ElementTree as ET
p=pathlib.Path(sys.argv[1]);r=ET.parse(p).getroot()
cs={x.get('ref'):x for x in r.findall('./components/comp')}
ns={x.get('name'):x for x in r.findall('./nets/net')}
by=collections.defaultdict(list);pins={}
for name,n in ns.items():
 for x in n.findall('node'):
  ref,pin=x.get('ref'),x.get('pin')
  by[name].append((ref,pin,x.get('pinfunction') or '',x.get('pintype') or ''))
  pins[(ref,pin)]=name
out=pathlib.Path(__file__).parent/'results';out.mkdir(exist_ok=True)
def csvout(filename,header,rows):
 with (out/filename).open('w',newline='',encoding='utf8') as f:
  w=csv.writer(f);w.writerow(header);w.writerows(rows)
ics=[(ref,cs[ref].findtext('value'),cs[ref].findtext('footprint'),pin,fn,name,typ) for name,nodes in by.items() for ref,pin,fn,typ in nodes if ref.startswith('U')]
csvout('ic_pins.csv',['ref','value','footprint','pin','function','net','type'],sorted(ics))
singles=[(n,len(v),'explicit NC' if n.startswith('unconnected-') else 'UNEXPECTED') for n,v in by.items() if len(v)==1]
csvout('single_nets.csv',['net','count','status'],singles)
diodes=[(ref,c.findtext('value'),c.findtext('footprint'),'; '.join(f'{pin}:{n}' for (rr,pin),n in pins.items() if rr==ref)) for ref,c in cs.items() if ref.startswith('D')]
csvout('diodes.csv',['ref','value','footprint','pins'],diodes)
connectors=[(ref,cs[ref].findtext('value'),pin,n) for (ref,pin),n in pins.items() if ref.startswith('J') and not ref.startswith('JP')]
csvout('connectors.csv',['ref','value','pin','net'],connectors)
direct=[(ref,pin,n,r,p,fn) for ref,_,pin,n in connectors if n!='GND' and not n.startswith('unconnected-') for r,p,fn,_ in by[n] if r.startswith('U')]
csvout('direct_ic_pins.csv',['connector','pin','net','IC','IC_pin','function'],direct)
# Conservative DC connectivity: R/F/L/FB/JP, and forward-oriented discrete diodes.
adj=collections.defaultdict(list);edges=[]
for ref,c in cs.items():
 pp=[(pin,n) for (rr,pin),n in pins.items() if rr==ref]
 if ref.startswith(('R','F','L','FB','JP')) and len(pp)==2:
  (_,a),(_,b)=pp
  adj[a].append((b,ref));adj[b].append((a,ref));edges.append((ref,a,b,'both'))
 if ref.startswith('D') and (c.findtext('value') or '').startswith(('BAT46','SS34','1N4148')):
  d=dict(pp)
  a=d.get('2') or d.get('A');k=d.get('1') or d.get('K')
  if a and k:adj[a].append((k,ref));edges.append((ref,a,k,'forward'))
csvout('conductive_edges.csv',['ref','from','to','direction'],edges)
rails={'+3V3','+5V','+12V','+3V3A','+5V_LCD1','+5V_LCD2'}
paths=[]
for ref,_,pin,start in connectors:
 if start=='GND' or start.startswith('unconnected-'):continue
 queue=collections.deque([(start,())]);seen={start};hits={}
 while queue:
  n,path=queue.popleft()
  if n in rails:hits[('rail',n)]=path
  for rr,pp,fn,_ in by[n]:
   if rr.startswith('U'):hits[('IC',f'{rr}.{pp}({fn})')]=path
  for nxt,via in adj[n]:
   if nxt not in seen:seen.add(nxt);queue.append((nxt,path+(via,)))
 for (kind,target),path in hits.items():paths.append((ref,pin,start,kind,target,' -> '.join(path) or 'DIRECT'))
csvout('dc_paths.csv',['connector','pin','net','target_type','target','via'],paths)
print('KiCad',r.findtext('./design/tool'),'components',len(cs),'nets',len(ns),'IC pins',len(ics))
print('connector pins',len(connectors),'single nets',len(singles),'unexpected',sum(x[2]=='UNEXPECTED' for x in singles))
print('diodes',len(diodes),'direct connector-to-IC pins',len(direct),'DC reachability records',len(paths))
for row in direct:
 if row[0] in ('J6','J17'):print('DIRECT',*row)
print('CSV output',out)
