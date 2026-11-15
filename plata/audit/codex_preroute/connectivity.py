"""Проверка медных связей по реальным формам pcbnew, включая каждую
отдельную область заполненных зон и сквозную связь через via/PTH.
Не считает всю цепь соединённой только по совпадению имени net.
"""
import sys,json,collections
import pcbnew
b=pcbnew.LoadBoard(sys.argv[1]);fp={f.GetReference():f for f in b.GetFootprints()}
layers=(pcbnew.F_Cu,pcbnew.In1_Cu,pcbnew.In2_Cu,pcbnew.B_Cu)
objects=collections.defaultdict(list);padids={};parents={}
def find(x):
 while parents[x]!=x:
  parents[x]=parents[parents[x]];x=parents[x]
 return x
def union(x,y):
 a,c=find(x),find(y)
 if a!=c:parents[c]=a
def add(net,key,layer,shape):
 parents.setdefault(key,key);bb=shape.BBox()
 objects[net,layer].append((key,shape,(bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom())))
for f in b.GetFootprints():
 for p in f.Pads():
  key=p.m_Uuid.AsString();padids[f.GetReference(),p.GetNumber(),key]=key
  for layer in layers:
   if p.GetNetname() and p.IsOnLayer(layer):add(p.GetNetname(),key,layer,p.GetEffectiveShape(layer))
for t in b.GetTracks():
 for layer in layers:
  if t.IsOnLayer(layer):add(t.GetNetname(),t.m_Uuid.AsString(),layer,t.GetEffectiveShape(layer))
for z in b.Zones():
 if z.GetIsRuleArea():continue
 for layer in layers:
  if not z.IsOnLayer(layer):continue
  allpoly=z.GetFilledPolysList(layer)
  for i in range(allpoly.OutlineCount()):
   poly=pcbnew.SHAPE_POLY_SET();poly.AddOutline(allpoly.COutline(i))
   for j in range(allpoly.HoleCount(i)):poly.AddHole(allpoly.CHole(i,j))
   add(z.GetNetname(),z.m_Uuid.AsString()+':'+str(layer)+':'+str(i),layer,poly)
needed=set()
tests=[]
def test(name,keys):
 pads=[]
 for ref,pin in keys:pads += [(ref,str(pin),p.m_Uuid.AsString(),p.GetNetname()) for p in fp[ref].Pads() if p.GetNumber()==str(pin)]
 assert pads and len({p[3] for p in pads})==1,(name,pads)
 needed.add(pads[0][3]);tests.append((name,pads))
for name,a,c in [
 ('W TX',[('U10',2),('U10',1)],[('T1',1),('T1',3)]),
 ('W RX',[('U10',6),('U10',5)],[('C64',1),('C65',1)]),
 ('RX caps',[('C64',2),('C65',2)],[('T1',6),('T1',8)]),
 ('A',[('T1',16),('T1',14)],[('T2',11),('T2',9)]),
 ('B',[('T1',11),('T1',9)],[('T2',16),('T2',14)]),
 ('P0 TX',[('U22',47),('U22',46)],[('T2',1),('T2',3)]),
 ('P0 RX',[('U22',44),('U22',45)],[('T2',6),('T2',8)]),
 ('P1 TX',[('U22',5),('U22',4)],[('J7',3),('J7',6)]),
 ('P1 RX',[('U22',2),('U22',3)],[('J7',1),('J7',2)]),
 ('P2 TX',[('U22',9),('U22',10)],[('J18',3),('J18',6)]),
 ('P2 RX',[('U22',12),('U22',11)],[('J18',1),('J18',2)]),
]:
 for i in (0,1):test(name+' '+str(i),[a[i],c[i]])
for name,keys in [
 ('T1 TX CT',[('T1',2),('C63',1),('R50',2)]),
 ('T1 RX CT',[('T1',7),('C66',1),('R51',2),('R52',1)]),
 ('RX bias P',[('T1',6),('R51',1)]),('RX bias N',[('T1',8),('R52',2)]),
 ('TX bias P',[('U10',2),('R48',1)]),('TX bias N',[('U10',1),('R49',1)]),
 ('T2 CT',[('T2',2),('T2',7),('C85',1)]),
 ('J7 CT',[('J7',4),('J7',5),('C67',1)]),('J18 CT',[('J18',4),('J18',5),('C109',1)]),
 ('SH1',[('J7',8),('J7','SH'),('C112',1),('R115',1)]),
 ('SH2',[('J18',8),('J18','SH'),('C114',1),('R118',1)]),
 ('GND RC/EP',[('J1',2),('U22',49),('C112',2),('C114',2),('R115',2),('R118',2),('C63',2),('C66',2),('C85',2),('C67',2),('C109',2)]),
 ('RST',[('U22',27),('R113',2),('C106',1)]),
 ('LED1',[('U22',30),('R54',1)]),('LED2',[('U22',32),('R114',1)]),
 ('USB DP',[('J5','A6'),('J5','B6'),('U9',1),('U9',6),('U8',1)]),
 ('USB DM',[('J5','A7'),('J5','B7'),('U9',3),('U9',4),('U8',2)]),
 ('CORE',[('U22',p) for p in (1,7,13,23,24,35,36,41,43)]+[('C'+str(n),1) for n in range(86,97)]),
 ('U22 VDD',[('L3',2)]+[('U22',p) for p in (6,8,18,31,37,38,48)]),
]:test(name,keys)
for (net,layer),entries in objects.items():
 if net not in needed:continue
 entries.sort(key=lambda e:e[2][0])
 for i,(key,shape,bb) in enumerate(entries):
  for other,other_shape,ob in entries[i+1:]:
   if ob[0]>bb[2]+2:break
   if ob[1]>bb[3]+2 or ob[3]<bb[1]-2 or find(key)==find(other):continue
   if shape.Collide(other_shape,2):union(key,other)
results={name:len({find(p[2]) for p in pads})==1 for name,pads in tests}
gndroot=next(p[2] for name,pads in tests if name=='GND RC/EP' for p in pads if p[0]=='J1')
gndvias=[v for v in b.GetTracks() if isinstance(v,pcbnew.PCB_VIA) and v.GetNetname()=='GND']
results['all GND vias']=all(find(v.m_Uuid.AsString())==find(gndroot) for v in gndvias)
root=next(p[2] for name,pads in tests if name=='U22 VDD' for p in pads if p[0]=='L3')
vdd={p[1]:find(p[2])==find(root) for name,pads in tests if name=='U22 VDD' for p in pads if p[0]=='U22'}
print(json.dumps({'checks':results,'gnd_vias':len(gndvias),'vdd_to_L3':vdd,'failed':[name for name,ok in results.items() if not ok]},ensure_ascii=False,indent=2))
if not all(results.values()):sys.exit(1)
