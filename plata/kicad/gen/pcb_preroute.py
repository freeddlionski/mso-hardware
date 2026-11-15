"""Закреплённые локальные соединения МСО74 после pcb_route.py init (KiCad 9).

Координаты — в системе placement.json, без ORIGIN. Схему и площадки не меняет.
Локальный поиск обходит РЕАЛЬНЫЕ формы площадок и ранее добавленную медь;
он применяется только внутри указанных ячеек, не заменяет общий трассировщик.
Неполучившееся соединение НЕ закрепляется: оно явно выводится в журнал/JSON.
Внешние зависимости, кроме pcbnew и стандартной библиотеки Python, не нужны.
"""
import collections
import fnmatch
import heapq
import json
import math
import os
import sys

import pcbnew

from pcb_build import mm, ORIGIN
import pcb_route
import pcb_rules

F, B = pcbnew.F_Cu, pcbnew.B_Cu
TAG = 'MSO74_PREROUTE_V1'


def xy(p):
    return (round(pcbnew.ToMM(p.x) - ORIGIN[0], 6), round(pcbnew.ToMM(p.y) - ORIGIN[1], 6))


def point(p):
    return pcbnew.VECTOR2I(mm(p[0] + ORIGIN[0]), mm(p[1] + ORIGIN[1]))


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def clearance(net):
    # Совпадает с приоритетами классов pcb_rules.project_json(): поздний класс выше.
    matched = [(list(pcb_rules.CLASSES).index(c), c) for c, p in pcb_rules.PATTERNS if fnmatch.fnmatchcase(net, p)]
    cls = max(matched)[1] if matched else 'Default'
    return pcb_rules.CLASSES[cls][1]


class Router:
    def __init__(self, board):
        self.board = board
        self.fp = {f.GetReference(): f for f in board.GetFootprints()}
        self.index = collections.defaultdict(list)
        self.serial = 0
        self.created = []
        self.paired = set()
        self.pairs = []
        self.edge_stitches = []
        self.done = []
        self.failed = []
        self.group = pcbnew.PCB_GROUP(board)
        self.group.SetName(TAG)
        self.group.SetLocked(True)
        board.Add(self.group)
        for f in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
            for p in f.Pads():
                for layer in (F, pcbnew.In2_Cu, B):
                    if p.IsOnLayer(layer):
                        self.obstacle(p, layer)
        for t in board.GetTracks():
            for layer in (F, pcbnew.In2_Cu, B):
                if t.IsOnLayer(layer):
                    self.obstacle(t, layer)

    def checkpoint(self):
        return len(self.created),len(self.done),self.serial,len(self.pairs)

    def rollback(self, checkpoint):
        count,done,serial,paircount=checkpoint
        for obj in self.created[count:]:
            self.group.RemoveItem(obj)
            self.board.Remove(obj)
        del self.created[count:];del self.done[done:];del self.pairs[paircount:];self.serial=serial
        self.index.clear()
        for f in sorted(self.board.GetFootprints(),key=lambda f:f.GetReference()):
            for p in f.Pads():
                for layer in (F,pcbnew.In2_Cu,B):
                    if p.IsOnLayer(layer):self.obstacle(p,layer)
        for t in self.board.GetTracks():
            for layer in (F,pcbnew.In2_Cu,B):
                if t.IsOnLayer(layer):self.obstacle(t,layer)

    def pad(self, ref, pin):
        pads = [p for p in self.fp[ref].Pads() if p.GetNumber() == str(pin)]
        if not pads:
            raise ValueError('нет площадки %s.%s' % (ref, pin))
        # У U1/ESP32 один номер у EP и множества PTH; берём самую большую медь.
        return max(pads, key=lambda p: p.GetSize().x * p.GetSize().y)

    def pos(self, ref, pin):
        return xy(self.pad(ref, pin).GetPosition())

    def add(self, obj):
        self.serial += 1
        obj.SetLocked(True)
        self.board.Add(obj)
        self.group.AddItem(obj)
        self.created.append(obj)
        return obj

    def obstacle(self, obj, layer):
        shape = obj.GetEffectiveShape(layer)
        bb = shape.BBox()
        p0, p1 = xy(bb.GetOrigin()), xy(bb.GetEnd())
        entry = (obj.GetNetname(), shape, obj)
        # Ячейка 2 мм — только пространственный индекс, не точность маршрута.
        for ix in range(math.floor(p0[0] / 2), math.floor(p1[0] / 2) + 1):
            for iy in range(math.floor(p0[1] / 2), math.floor(p1[1] / 2) + 1):
                self.index[layer, ix, iy].append(entry)

    def free(self, a, b, width, net, layer=F, ignore=()):
        r = width / 2 + 0.32
        # Кромка и механические запреты из pcb_route.init, включая шайбы M3.
        if any(x < .3 + width / 2 or x > 239.7 - width / 2 or
               y < .3 + width / 2 or y > 119.7 - width / 2 for x, y in (a, b)):
            return False
        segment = pcbnew.SHAPE_SEGMENT(point(a), point(b), mm(width))
        for hx, hy in pcb_route.HOLES:
            if segment.Collide(point((hx, hy)), mm(3.61)):
                return False
        seen = set()
        for ix in range(math.floor((min(a[0], b[0]) - r) / 2), math.floor((max(a[0], b[0]) + r) / 2) + 1):
            for iy in range(math.floor((min(a[1], b[1]) - r) / 2), math.floor((max(a[1], b[1]) + r) / 2) + 1):
                for other, shape, obj in self.index[layer, ix, iy]:
                    if (other == net and not (getattr(self,'block_own',None)==(net,layer) and isinstance(obj,pcbnew.PCB_TRACK) and not isinstance(obj,pcbnew.PCB_VIA))) or other in ignore or id(obj) in seen:
                        continue
                    seen.add(id(obj))
                    # 5 нм допуска только на округление offset-пары в единицы KiCad; DRC не меняется.
                    gap = max(clearance(net), clearance(other), .15) + (-.000005 if frozenset((net,other)) in self.paired else .006)
                    if shape.Collide(segment, mm(gap)):
                        return False
        return True

    def track(self, pts, net, width, layer=F, label=''):
        if width < pcb_rules.RULES['min_track_width']:
            raise ValueError('дорожка тоньше правил')
        if any(not self.free(a, b, width, net, layer) for a, b in zip(pts, pts[1:])):
            return False
        item_ids=[]
        for a, b in zip(pts, pts[1:]):
            if distance(a, b) < .00001:
                continue
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(point(a)); t.SetEnd(point(b)); t.SetWidth(mm(width))
            t.SetLayer(layer); t.SetNet(self.board.FindNet(net))
            self.add(t); self.obstacle(t, layer)
            item_ids.append(t.m_Uuid.AsString())
        self.done.append({'label': label, 'net': net, 'layer': self.board.GetLayerName(layer),
                          'width_mm': width, 'item_uuids':item_ids,'start_mm':pts[0],'end_mm':pts[-1], 'length_mm': round(sum(distance(a, b) for a, b in zip(pts, pts[1:])), 6)})
        return True

    def search(self, start, goal, net, width, layer=F, margin=2, step=.1, ignore=(), gate=None,max_nodes=80000):
        def facing(a,b):
            if gate is None:return True
            da,db=gate
            if distance(a,start)<.00001 and sum((b[i]-start[i])*da[i] for i in (0,1))<-.00001:return False
            if distance(b,goal)<.00001 and sum((a[i]-goal[i])*db[i] for i in (0,1))<-.00001:return False
            return True
        if facing(start,goal) and self.free(start, goal, width, net, layer, ignore):
            return [start, goal]
        x0, x1 = min(start[0], goal[0]) - margin, max(start[0], goal[0]) + margin
        y0, y1 = min(start[1], goal[1]) - margin, max(start[1], goal[1]) + margin
        # Сетка привязана к точному start. Старая глобальная сетка давала
        # микросегменты назад у start/goal; offset превращал их в развороты.
        def coord(n):
            return round(start[0]+n[0]*step,6),round(start[1]+n[1]*step,6)
        s=(0,0)
        if not self.free(start,start,width,net,layer,ignore) or not self.free(goal,goal,width,net,layer,ignore):
            return None
        queue = [(distance(start, goal), 0., s)]
        cost, parent = {s: 0.}, {}
        visited = 0
        directions = ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1))
        while queue:
            _, d, n = heapq.heappop(queue)
            if d > cost[n] + 1e-8:
                continue
            at=coord(n)
            # Последний отрезок идёт прямо в точный goal, с верной стороны.
            # Никакого round(goal) → goal с противоположным направлением.
            if distance(at,goal)<=step*1.5 and facing(at,goal) and self.free(at,goal,width,net,layer,ignore):
                route = [n]
                while n != s:
                    n = parent[n]; route.append(n)
                route = [start] + [coord(n) for n in reversed(route)] + [goal]
                # Удаление коллинеарных точек; никаких срезов углов через препятствие.
                out = []
                for p in route:
                    if out and distance(p, out[-1]) < .00001:
                        continue
                    while len(out) > 1:
                        a, b = out[-2:]
                        cross = (b[0]-a[0])*(p[1]-b[1])-(b[1]-a[1])*(p[0]-b[0])
                        if abs(cross) > 1e-7:
                            break
                        out.pop()
                    out.append(p)
                # Убираем лестницы 0,1 мм: offset двух лестниц давал бы
                # самопересечения на каждом коротком колене. Любой новый
                # отрезок снова проверяется полной формой меди.
                smooth=[out[0]];i=0
                while i<len(out)-1:
                    j=len(out)-1
                    while j>i+1 and not (facing(out[i],out[j]) and self.free(out[i],out[j],width,net,layer,ignore)):
                        j-=1
                    smooth.append(out[j]);i=j
                return smooth
            visited += 1
            if visited > max_nodes:
                return None
            a = coord(n)
            for dx, dy in directions:
                q = n[0] + dx, n[1] + dy
                b = coord(q)
                if not (x0 <= b[0] <= x1 and y0 <= b[1] <= y1):
                    continue
                if gate is not None:
                    da,db=gate
                    if distance(b,start)<1.0 and sum((b[i]-start[i])*da[i] for i in (0,1))<-.11:continue
                    if distance(b,goal)<1.0 and sum((b[i]-goal[i])*db[i] for i in (0,1))<-.11:continue
                nd = d + step * (math.sqrt(2) if dx and dy else 1)
                if nd >= cost.get(q, math.inf) - 1e-9:
                    continue
                if not self.free(a, b, width, net, layer, ignore):
                    continue
                cost[q] = nd; parent[q] = n
                heapq.heappush(queue, (nd + distance(b, goal), nd, q))
        return None

    def connect(self, a, b, width=.2, margin=2, step=.1, layer=F, label=''):
        pa, pb = self.pad(*a), self.pad(*b)
        net = pa.GetNetname()
        if not net or net != pb.GetNetname():
            raise ValueError('соединение разных цепей %s %s' % (a, b))
        route = self.search(xy(pa.GetPosition()), xy(pb.GetPosition()), net, width, layer, margin, step)
        label = label or '%s.%s—%s.%s' % (*a, *b)
        if route is None or not self.track(route, net, width, layer, label):
            self.failed.append(label)
            print('НЕ РАЗВЕДЕНО:', label, flush=True)
            return False
        print('разведено:', label, flush=True)
        return True

    def canvia(self, pos, net='GND', diameter=.6, drill=.3):
        if any(not self.free(pos, pos, diameter, net, layer) for layer in (F, pcbnew.In2_Cu, B)):
            return None
        # Via проходит сквозь все слои: платы init не содержат внутренние дорожки,
        # внутренние зоны обтекают via при refill. Минимум отверстие–отверстие 0,2.
        for f in self.fp.values():
            for p in f.Pads():
                size = p.GetDrillSize()
                if size.x and size.y:
                    # Консервативная окружность вокруг отверстия/слота.
                    if distance(pos, xy(p.GetPosition())) < (max(size.x, size.y) / 1e6 + drill) / 2 + .206:
                        return None
        for t in self.board.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA) and distance(pos, xy(t.GetPosition())) < (pcbnew.ToMM(t.GetDrill()) + drill) / 2 + .206:
                return None
        return True

    def via(self, pos, net='GND', diameter=.6, drill=.3):
        if not self.canvia(pos,net,diameter,drill):
            return None
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(point(pos)); v.SetWidth(F, mm(diameter)); v.SetDrill(mm(drill))
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(F, B)
        v.SetNet(self.board.FindNet(net)); self.add(v)
        self.obstacle(v, F); self.obstacle(v, pcbnew.In2_Cu); self.obstacle(v, B)
        return v

    def copper(self, net, rect, layer=F, priority=10, name=''):
        # Явно задаём наибольший зазор классов (.30 мм). Даже при создании
        # платы и refill в одном pcbnew-процессе (кеш проекта до записи .pro)
        # зона не сможет залиться на .20/.25 мм от соседней цепи 24 В.
        gap=max(c[1] for c in pcb_rules.CLASSES.values())
        z = pcb_route.zone(self.board, net, layer, rect, priority, gap, thermal=False)
        # zone() уже добавил объект в BOARD.
        self.serial += 1
        z.SetZoneName(TAG + ':' + name)
        z.SetLocked(True); self.group.AddItem(z); self.created.append(z)
        return z


def power(r):
    """Сплошная медь расширяет короткие выводы, а не 5 А по длинному neckdown.

    Зоны clip-ятся KiCad по чужим площадкам с реальным зазором; SW не
    объединяется с GND: pin 10 LM61460 — именно коммутационный узел.
    """
    for u, l, bulk, j, y, cin, cout, fb, cvcc, cb, rb in [
        ('U5','L4','C34','J3',26,('C24','C25','C26','C27','C110'),('C30','C31','C32','C33'),('R30','R31'),'C28','C29','R29'),
        ('U6','L5','C45','J4',56,('C35','C36','C37','C38','C111'),('C41','C42','C43','C44'),('R37','R38'),'C39','C40','R36')]:
        out = r.pad(l,2).GetNetname()
        r.copper(out, (5, y-10, 30.1, y+8), name=u+':COUT-J')
        r.copper(r.pad(u,10).GetNetname(), (38.3,y-.9,46.2,y+.9), name=u+':SW')
        # Отдельные верхняя/нижняя входные ячейки, короткие керамические петли.
        for c, pin in [(cin[2],12),(cin[3],8)]:
            start,end=r.pos(u,pin),r.pos(c,1)
            # До y±2.3 держим VIN строго по оси вывода: диагональ раньше
            # перекрывала единственный коридор SW→BOOT между VIN и RBOOT.
            elbow=(start[0],y+(2.4 if pin==12 else -2.4))
            net=r.pad(u,pin).GetNetname()
            if not r.track([start,elbow,end],net,.3,label=u+' VIN ceramic'):
                r.failed.append(u+' VIN ceramic')
        for a,b in [(cin[0],cin[2]),(cin[1],cin[3]),(cin[0],cin[4])]:
            r.connect((a,1),(b,1),.6,margin=2)
        r.connect((u,10),(l,1),.3,margin=1,step=.05)
        for c in cout:
            r.connect((l,2),(c,1),.6,margin=2)
        r.connect((cout[0],1),(bulk,1),3,margin=4)
        r.connect((bulk,1),(j,1),3,margin=5)
        # FB берётся от COUT, отдельно от шумного узла SW.
        for a,b,w in [((u,10),(cb,2),.15),((u,4),(fb[1],1),.15),((fb[1],1),(fb[0],2),.2),
                       ((u,2),(cvcc,1),.2),((u,14),(cb,1),.15),
                       ((rb,2),(cb,1),.15)]:
            r.connect(a,b,w,margin=2,step=.05)
        # BIAS и верхний FB — малоточный Kelvin-подвод от выхода по B.Cu;
        # не проводим цепь обратной связи через hot loop на F.Cu.
        kelvin(r,(u,13),(rb,1),.15,diameter=.45,drill=.2,source_via=(46.9,y+.6))
        kelvin(r, (fb[0],1), (cout[0],1), .2)
        sense_branch(r,(u,1),r.pad(u,1).GetNetname())
        r.copper('GND',(42.6,y-1.15,44.0,y+1.15),B,name=u+':PGND-back')
    for u,l,cin,cb,cout,fb in [
        ('U2','L1',('C6','C7'),'C8',('C9','C10','C115','C11'),('R13','R14')),
        ('U3','L2',('C12','C13'),'C14',('C15','C16','C17'),('R18','R19')),
        ('U4','L3',('C18','C19'),'C20',('C21','C22','C23'),('R23','R24'))]:
        sx,sy=r.pos(u,2); lx,ly=r.pos(l,1)
        r.copper(r.pad(u,2).GetNetname(), (sx-.45,sy-.3,lx+.45,ly+.8),name=u+':SW')
        for a,b,w in [((u,3),(cin[1],1),.3),((cin[1],1),(cin[0],1),.6),
                       ((u,2),(l,1),.3),((u,6),(cb,1),.2),((u,2),(cb,2),.2),
                       ((u,4),(fb[0],2),.2),((fb[0],2),(fb[1],1),.2)]:
            r.connect(a,b,w,margin=2,step=.05)
        for c in cout:
            r.connect((l,2),(c,1),.6,margin=3)
        kelvin(r,(fb[0],1),(cout[0],1),.2)
    # Вход: площадки F1 — PTH. Основной путь 6 А на B.Cu не пересекает
    # чувствительные UVLO/OVP/ILIM на верхней стороне TPS26631.
    r.connect(('J1',1),('F1',1),4,margin=3,layer=B)
    r.connect(('F1',2),('D1',1),4,margin=5,layer=B)
    # По B.Cu широкая VIN_F медь от F1/TVS, по F.Cu — компактный остров
    # только у истоков Q1. Переходы ниже устанавливаются массивом.
    r.copper('VIN_F',(22,80.5,43,105),B,name='input:VIN_F')
    r.copper('VIN_F',(40.5,80.8,43.8,85.2),name='Q1:source')
    vinb=r.pad('U1',1).GetNetname()
    r.copper(vinb,(29.4,79.2,31.9,82.9),name='U1:VIN')
    r.copper(vinb,(29.4,76.0,49.4,80.2),name='Q1-U1:VIN-top')
    r.copper(vinb,(44.1,78,49.4,86.4),name='Q1:drain')
    r.copper('+24V_P',(36.2,79.2,39.1,82.9),name='U1:OUT')
    # 15 PTH EP21 остаются из footprint. Локальная нижняя медь отводит
    # тепло в In1 через них; ни одного отверстия не удаляем и не добавляем туда.
    r.copper('GND',(30,80,38,88),B,priority=20,name='U1:thermal')
    for y in (81.5,82.3,83.1,83.9,84.7):
        r.via((41.3,y),'VIN_F',.6,.3)
    for x in (37.4,38.2):
        for y in (79.7,80.5):
            r.via((x,y),'+24V_P',.6,.3)

    # +24V_P от In2 к входной керамике, по 2–3 независимых подвода ячейки.
    # Не оставлять надежду на последующий автоматический fanout питания.
    for ref in ('C6','C12','C18','C24','C25','C110','C35','C36','C111'):
        p=r.pad(ref,1);net=p.GetNetname();x,y=xy(p.GetPosition())
        bb=p.GetBoundingBox();hx=pcbnew.ToMM(bb.GetWidth())/2;hy=pcbnew.ToMM(bb.GetHeight())/2
        placed=0
        for q in [(x,y+hy+.5),(x,y-hy-.5),(x+hx+.5,y),(x-hx-.5,y)]:
            if r.free((x,y),q,.6,net) and r.via(q,net):
                r.track([(x,y),q],net,.6,label=ref+' VIN via');placed+=1
            if placed==2:break
        if not placed:r.failed.append(ref+' VIN via')
    # LMR 3V3 стоит слева от границы x=82: via здесь попал бы в 24V,
    # поэтому отдельная широкая магистраль к массиву уже справа от границы.
    q=(85.3,79.6);start=r.pos('C23',1)
    route=[start,(start[0],80.5),(85.3,80.5),q]
    if route and r.track(route,'+3V3',1.5,label='LMR3V3 to In2'):
        r.copper('+3V3',(83.5,78.5,87.0,80.7),name='3V3:plane-entry')
        for x in (84.5,85.3,86.1):
            for y in (79.2,80.0):r.via((x,y),'+3V3')
    else:r.failed.append('LMR3V3 to In2')
    # IN_SYS должен видеть VIN_F до защиты обратной полярности.
    r.track([r.pos('U1',6),(29.5,84.325)],'VIN_F',.25,label='U1 IN_SYS')
    r.via((29.5,84.325),'VIN_F')


def kelvin(r,a,b,width,diameter=.6,drill=.3,source_via=None):
    """Короткие выводы на F, измерительная цепь по B, без пробивки In1/In2."""
    pa,pb=r.pad(*a),r.pad(*b);net=pa.GetNetname()
    if net!=pb.GetNetname():
        raise ValueError('Kelvin: разные цепи')
    positions=[]; stems=[]
    for i,p in enumerate((pa,pb)):
        center=xy(p.GetPosition()); choices=[]
        if i==0 and source_via is not None:
            if r.free(center,source_via,width,net) and r.canvia(source_via,net,diameter,drill):choices=[source_via]
        for radius in (.8,1.1,1.5,2.0):
            if choices:break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)):
                q=(center[0]+radius*dx,center[1]+radius*dy)
                if r.free(center,q,width,net) and r.canvia(q,net,diameter,drill):
                    choices.append(q)
            if choices:break
        if not choices:
            r.failed.append('Kelvin %s.%s' % (p.GetParentFootprint().GetReference(),p.GetNumber()));return
        positions.append(choices[0]);stems.append([center,choices[0]])
    path=r.search(*positions,net,width,B,margin=3)
    if path is None:
        r.failed.append('Kelvin %s—%s' % (a,b));return
    # Via может не пройти по отверстиям. Не оставлять незаконченные стволы.
    before=len(r.created)
    vias=[r.via(q,net,diameter,drill) for q in positions]
    if not all(vias):
        for obj in r.created[before:]:
            r.group.RemoveItem(obj);r.board.Remove(obj)
        # Эта ситуация должна обнаруживаться при локальной проверке, а не
        # маскироваться работой автотрассировщика.
        raise RuntimeError('не удалось поставить Kelvin via: '+str(a))
    for stem in stems:r.track(stem,net,width)
    r.track(path,net,width,B,label='Kelvin %s—%s' % (a,b))


def clocks(r):
    for u,yi,yo,y,caps in [('U10',30,31,'Y1',('C61','C62')),
                           ('U22',40,39,'Y3',('C107','C108')),
                           ('U19',1,2,'Y2',('C81',))]:
        # Сначала внешний XO: внутренний XI затем не отрезает его выход.
        r.connect((u,yo),(y,3 if y!='Y2' else 2),.15,margin=4,step=.05)
        r.connect((u,yi),(y,1),.15,margin=4,step=.05)
        for pin,c in zip((1,3),caps):
            # C81 DNP остаётся площадкой XI, не устанавливаем новый конденсатор.
            r.connect((y,pin),(c,1),.15,margin=2,step=.05)
    r.connect(('Y1',1),('R47',1),.15,margin=2,step=.05)
    r.connect(('Y1',3),('R47',2),.15,margin=2,step=.05)


def offset(poly, delta):
    """Параллельная ломаная с miter-стыками; delta > 0 слева по ходу."""
    normals=[]
    for a,b in zip(poly,poly[1:]):
        length=distance(a,b)
        normals.append((-(b[1]-a[1])/length,(b[0]-a[0])/length))
    result=[]
    for i,(x,y) in enumerate(poly):
        if i==0:nx,ny=normals[0]
        elif i==len(poly)-1:nx,ny=normals[-1]
        else:
            u,v=normals[i-1],normals[i]
            denominator=1+u[0]*v[0]+u[1]*v[1]
            if denominator<.1:raise ValueError('разворот пары на месте')
            nx,ny=(u[0]+v[0])/denominator,(u[1]+v[1])/denominator
        result.append((round(x+nx*delta,6),round(y+ny*delta,6)))
    return result


def pair_paths(r,name,paths,width,neck_first=False):
    """Обе линии одной транзакцией: частично закреплённая пара запрещена."""
    checkpoint=r.checkpoint()
    nets=[net for net,pts in paths]
    r.paired.add(frozenset(nets))
    for net,pts in paths:
        ok=(r.track(pts[:2],net,.15,label=name+' connector neck') and
            r.track(pts[1:],net,width,label=name)) if neck_first else r.track(pts,net,width,label=name)
        if not ok:
            r.rollback(checkpoint);r.failed.append(name);return False
    lengths=[sum(distance(a,b) for a,b in zip(pts,pts[1:])) for net,pts in paths]
    if abs(lengths[0]-lengths[1])>.5:
        r.rollback(checkpoint);r.failed.append(name+' перекос >0,5 мм');return False
    r.pairs.append({'name':name,'nets':nets,'layer':'F.Cu','width_mm':width,'gap_mm':.2,
                    'lengths_mm':[round(v,6) for v in lengths],'skew_mm':round(abs(lengths[0]-lengths[1]),6)})
    return True


def usb(r):
    dp=r.pad('U8',1).GetNetname();dm=r.pad('U8',2).GetNetname()
    for ref,pos in [('U8',(216,68)),('U9',(226,68))]:
        if distance(xy(r.fp[ref].GetPosition()),pos)>.001 or r.fp[ref].GetOrientationDegrees()!=0:
            raise ValueError('USB: изменилась раскладка '+ref)
    # USB-C контакты в порядке DP-DM-DP-DM. DP объединяется справа от
    # площадок, DM слева; главная пара выходит с наружных B6/B7. Поэтому
    # перекрёста нет и все контакты соединены на F.Cu. От A6/A7 добавляется
    # 3,03 / 3,07 мм соответственно (перекос обеих ориентаций <=0,04 мм).
    first=[(dp,[r.pos('J5','B6'),(231.2,67.25),(230.5,67.25),(229.995,67.755),
                (228.5,67.755),(227.795,67.05),r.pos('U9',6)]),
           (dm,[r.pos('J5','B7'),(231.2,68.75),(230.5,68.75),(229.995,68.245),
                (228.5,68.245),(227.795,68.95),r.pos('U9',4)])]
    if pair_paths(r,'USB J5 B6/B7—USBLC6',first,.29,neck_first=True):
        cp=r.checkpoint()
        copies=[(dp,[r.pos('J5','A6'),(233.6,68.25),(233.6,67.25),r.pos('J5','B6')]),
                (dm,[r.pos('J5','A7'),(231.55,67.75),(231.55,68.75),r.pos('J5','B7')])]
        if all(r.track(pts,net,.15,label='USB-C copies F') for net,pts in copies):
            lengths=[sum(distance(a,b) for a,b in zip(pts,pts[1:])) for net,pts in copies]
            r.pairs.append({'name':'USB-C A6/A7—B6/B7 copies','nets':[dp,dm],'layer':'F.Cu',
                            'width_mm':.15,'gap_mm':None,'lengths_mm':[round(v,6) for v in lengths],
                            'skew_mm':round(abs(lengths[0]-lengths[1]),6),
                            'note':'короткий fanout, не контролируемая по импедансу пара'})
        else:r.rollback(cp);r.failed.append('USB-C copies F')
    # CH340K имеет USB на левой стороне. Пара проходит над EP сверху и
    # заходит с внутренней стороны площадок 1/2. Здесь нельзя вести её
    # напрямую через GND EP; x=214,35 оставляет >=0,20 мм до EP слева.
    center=[(223,68),(222,68),(220.5,66.5),(220.5,64.2),(214.35,64.2),(214.35,66.5),(213.9,66.5)]
    p,n=offset(center,.245),offset(center,-.245)
    second=[(dp,[r.pos('U9',1),(223.8,67.05),(223.095,67.755)]+p+[(213.645,66),r.pos('U8',1)]),
            (dm,[r.pos('U9',3),(223.8,68.95),(223.095,68.245)]+n+[(213.645,67),r.pos('U8',2)])]
    pair_paths(r,'USB USBLC6—CH340K',second,.29)
    # Явная медь проходных каналов USBLC6: native DSN/DRC не должны
    # надеяться на внутреннее соединение выводов 1↔6 / 3↔4.
    through=[(dp,[r.pos('U9',6),r.pos('U9',1)]),(dm,[r.pos('U9',4),r.pos('U9',3)])]
    if pair_paths(r,'USBLC6 flow-through',through,.29):
        r.pairs[-1]['gap_mm']=round(abs(r.pos('U9',1)[1]-r.pos('U9',3)[1])-.29,6)
        r.pairs[-1]['note']='короткие параллельные каналы между проходными выводами корпуса'


def simple_path(points):
    """Запрет петли/наложения: совпадение общей длины не доказывает skew,
    если собственная медь замыкает согласующий участок более коротким путём.
    """
    pts=[]
    for p in points:
        if not pts or distance(pts[-1],p)>.00001:pts.append(p)
    def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for a,b,c in zip(pts,pts[1:],pts[2:]):
        ab=(b[0]-a[0],b[1]-a[1]);bc=(c[0]-b[0],c[1]-b[1])
        if (ab[0]*bc[0]+ab[1]*bc[1])/(distance(a,b)*distance(b,c))<-.8:return False
    for i,(a,b) in enumerate(zip(pts,pts[1:])):
        for j in range(i+2,len(pts)-1):
            c,d=pts[j:j+2]
            if max(min(a[0],b[0]),min(c[0],d[0]))>min(max(a[0],b[0]),max(c[0],d[0]))+.00001:continue
            if max(min(a[1],b[1]),min(c[1],d[1]))>min(max(a[1],b[1]),max(c[1],d[1]))+.00001:continue
            if cross(a,b,c)*cross(a,b,d)<=1e-12 and cross(c,d,a)*cross(c,d,b)<=1e-12:return False
    return True


def route_pair(r,name,a,b,out_a,out_b,escape_a=1.4,escape_b=1.8,margin=8,
               layer=F,endpoints=None,ribbon=.74,heading_a=None,heading_b=None,length_bias=(0.,0.),end_parallel=None,end_shift=(0.,0.),waypoints=None):
    """Общий коридор и две линии .24/.20; сначала ОБЕ магистрали, затем fanout.

    Если создавать первый fanout до второй линии, он мог занять место
    второй линии — ложный тупик первой версии. Проверяем каждую offset-
    линию реальной формой меди, поэтому коридор .74 мм не ослабляет DRC.
    """
    pads=[r.pad(*p) for p in a+b]
    if pads[0].GetNetname()!=pads[2].GetNetname() or pads[1].GetNetname()!=pads[3].GetNetname():
        raise ValueError('не совпали сети пары '+name)
    nets=[pads[0].GetNetname(),pads[1].GetNetname()]
    r.paired.add(frozenset(nets))
    positions=endpoints or [xy(p.GetPosition()) for p in pads]
    ma=tuple((positions[0][i]+positions[1][i])/2 for i in (0,1))
    mb=tuple((positions[2][i]+positions[3][i])/2 for i in (0,1))
    ca=tuple(ma[i]+out_a[i]*escape_a for i in (0,1))
    cb=tuple(mb[i]+out_b[i]*escape_b+end_shift[i] for i in (0,1))
    ha,hb=heading_a or out_a,heading_b or out_b
    sa=tuple(ca[i]+ha[i]*.6 for i in (0,1))
    sb=tuple(cb[i]+hb[i]*.6 for i in (0,1))
    sign=(positions[0][0]-positions[1][0])*(-out_a[1])+(positions[0][1]-positions[1][1])*out_a[0]
    end_sign=(positions[2][0]-positions[3][0])*out_b[1]-(positions[2][1]-positions[3][1])*out_b[0]
    if sign*end_sign<=0:
        raise ValueError('инверсия порядка проводников '+name)
    delta=.22 if sign>0 else -.22
    # Имена обеих цепей нельзя игнорировать: средняя линия тогда
    # пересекала площадку N, и смещённая дорожка P замыкалась на неё.
    # __PAIR_CORRIDOR__ имеет clearance .20 и видит ВСЕ площадки.
    if waypoints:
        route=[sa]
        for target in list(waypoints)+[sb]:
            piece=r.search(route[-1],target,'__PAIR_CORRIDOR__',ribbon,layer,margin=2,step=.1,max_nodes=30000)
            if piece is None:route=None;break
            route+=piece[1:]
    else:
        route=r.search(sa,sb,'__PAIR_CORRIDOR__',ribbon,layer,margin=margin,step=.2,gate=(ha,hb),max_nodes=60000)
        if route is None and ribbon==.74:
            route=r.search(sa,sb,'__PAIR_CORRIDOR__',ribbon,layer,margin=margin,step=.1,gate=(ha,hb),max_nodes=100000)
    if route is None:
        if os.environ.get('PCB_PREROUTE_DEBUG'):
            print('corridor fail',name,layer,ribbon,sa,sb,flush=True)
        r.failed.append(name+' (нет общего коридора)');return False
    try:middle=[offset([ca]+route+[cb],delta),offset([ca]+route+[cb],-delta)]
    except ValueError:r.failed.append(name+' (разворот коридора)');return False
    cp=r.checkpoint()
    if not all(r.track(middle[i],nets[i],.24,layer,label=name) for i in (0,1)):
        r.rollback(cp);r.failed.append(name+' (offset/clearance)');return False
    sections=[]
    for i in (0,1):
        # .15 требуется у .4-мм ряда QFN; крупные площадки не сужаем.
        w_start=.15 if layer==F and distance(positions[i],xy(pads[i].GetPosition()))<.01 and min(pads[i].GetSize().x,pads[i].GetSize().y)<mm(.24) else .24
        w_end=.15 if layer==F and min(pads[i+2].GetSize().x,pads[i+2].GetSize().y)<mm(.24) else .24
        start=r.search(positions[i],middle[i][0],nets[i],w_start,layer,margin=3,step=.05)
        if start is None or not r.track(start,nets[i],w_start,layer,label=name):
            r.rollback(cp);r.failed.append(name+' (start fanout)');return False
        target=end_parallel[i] if end_parallel else positions[i+2]
        end=r.search(middle[i][-1],target,nets[i],w_end,layer,margin=3,step=.05)
        if end and end_parallel:end=end+[positions[i+2]]
        if end is None or not r.track(end,nets[i],w_end,layer,label=name):
            r.rollback(cp);r.failed.append(name+' (end fanout)');return False
        sections.append([(start,w_start),(middle[i],.24),(end,w_end)])
    r.rollback(cp)
    def lengths(candidate):
        return [sum(distance(a,b) for p,w in pieces for a,b in zip(p,p[1:]))+length_bias[i] for i,pieces in enumerate(candidate)]
    ls=lengths(sections);diff=abs(ls[0]-ls[1]);attempts=[sections]
    def fan_length(pts,sec):
        last=len(pts)-2 if sec==2 and end_parallel else len(pts)-1
        return sum(distance(pts[j],pts[j+1]) for j in range(last))
    raw_fan=[[fan_length(sections[i][j][0],j) for j in (0,2)] for i in (0,1)]
    if diff>.5:
        short=0 if ls[0]<ls[1] else 1;attempts=[]
        # Не растягивать один вывод на 4–6 мм ради нулевого skew.
        # Компенсация делится между двумя короткими fanout; целевой
        # остаток .35 мм даёт запас к пределу .50 мм.
        added=diff-.35
        room=[max(0.,3.-raw_fan[short][k]) for k in (0,1)]
        weighted=room[0]/sum(room) if sum(room)>0 else .5
        def variants(sec,amount):
            pts,w=sections[short][sec]
            if amount<1e-6:return [pts]
            if fan_length(pts,sec)+amount>3.+1e-6:return []
            result=[];limit=len(pts)-2 if sec==2 and end_parallel else len(pts)-1
            for j in range(limit):
                a0,b0=pts[j:j+2];length=distance(a0,b0)
                if length<.4:continue
                vx,vy=(b0[0]-a0[0])/length,(b0[1]-a0[1])/length
                for size in (.6,.9,1.2,1.5,.4):
                    base=min(length,size,3-amount)
                    if base<.4:continue
                    for along in (length-base,(length-base)/2,0):
                        q0=(a0[0]+vx*along,a0[1]+vy*along);q1=(q0[0]+vx*base,q0[1]+vy*base)
                        for side in (-1,1):
                            nx,ny=-vy*side*amount/2,vx*side*amount/2
                            result.append(pts[:j+1]+[q0,(q0[0]+nx,q0[1]+ny),(q1[0]+nx,q1[1]+ny),q1]+pts[j+1:])
            return result[:60]
        for fraction in (1.,0.,weighted,.5,.6,.4,.25,.75):
            src=variants(0,added*fraction);end=variants(2,added*(1-fraction))
            for start in src:
                for finish in end:
                    candidate=[[(list(p),w) for p,w in pieces] for pieces in sections]
                    candidate[short][0]=(start,sections[short][0][1])
                    candidate[short][2]=(finish,sections[short][2][1])
                    attempts.append(candidate)
    for candidate in attempts:
        if not all(simple_path([p for points,w in candidate[i] for p in points]) for i in (0,1)):continue
        ok=all(r.track(candidate[i][1][0],nets[i],.24,layer,label=name) for i in (0,1))
        if ok:
            for i in (0,1):
                for sec in (0,2):
                    pts,w=candidate[i][sec]
                    if not r.track(pts,nets[i],w,layer,label=name):ok=False;break
                if not ok:break
        if ok:
            ls=lengths(candidate)
            fan=[[sum(distance(a,b) for a,b in zip(candidate[i][j][0],candidate[i][j][0][1:])) for j in (0,2)] for i in (0,1)]
            r.pairs.append({'name':name,'nets':nets,'layer':r.board.GetLayerName(layer),'width_mm':.24,'gap_mm':.2,
                            'fanout_lengths_mm':fan,
                            'unpaired_fanout_lengths_mm':[[fan_length(candidate[i][j][0],j) for j in (0,2)] for i in (0,1)],
                            'parallel_tail_lengths_mm':[distance(candidate[i][2][0][-2],candidate[i][2][0][-1]) if end_parallel else 0 for i in (0,1)],
                            'length_bias_mm':list(length_bias),'lengths_mm':[round(x,6) for x in ls],
                            'skew_mm':round(abs(ls[0]-ls[1]),6)})
            print('пара:',name,ls,flush=True);return True
        r.rollback(cp)
    r.failed.append(name+' (согласование/зазор)');return False


def pair_return_vias(r,points):
    """Два коротких возврата на In1 рядом с переходом пары, не на ETH_SH."""
    result=[]
    for p in points:
        existing=[xy(v.GetPosition()) for v in r.board.GetTracks() if isinstance(v,pcbnew.PCB_VIA) and v.GetNetname()=='GND']
        if any(distance(p,q)<=2.5 for q in existing):continue
        for radius in (1.0,1.3,1.6,1.9,2.2,2.5,3.):
            for angle in range(0,360,30):
                a=math.radians(angle);q=(round(p[0]+radius*math.cos(a),6),round(p[1]+radius*math.sin(a),6))
                if r.via(q,'GND',.45,.2):result.append(q);break
            else:continue
            break
        else:return None
    return result


def drop_created(r,ids):
    ids=set(ids)
    for obj in list(r.created):
        if obj.m_Uuid.AsString() in ids:
            r.group.RemoveItem(obj);r.board.Remove(obj);r.created.remove(obj)
    r.done[:]=[v for v in r.done if not any(u in ids for u in v['item_uuids'])]
    r.rollback(r.checkpoint())


def hybrid_pair(r,name,a,b,heads,bias,oa,ob,surface):
    """Обход топологического пересечения пар: законченная B-пара до
    симметричных via в свободной ячейке, затем F над In1 до назначения.
    Никаких одиночных переходов/несогласованных концов.
    """
    recipes={
      'ETH RTL port0 RX—T2':[(211,29.5),(-1,0),(1,0),4.8],
      'ETH RTL port1 TX—J7':[(211,27),(1,0),(1,0),3.53],
      'ETH RTL port2 TX—J18':[(213,53),(1,0),(-1,0),2.8],
      'ETH RTL port2 RX—J18':[(212.5,56),(1,0),(1,0),2.8],
    }
    if name not in recipes:return False
    center,fo,fe,eb=recipes[name];cp=r.checkpoint();nf=len(r.failed)
    nets=[r.pad(*p).GetNetname() for p in a]
    sign=(heads[0][0]-heads[1][0])*(-oa[1])+(heads[0][1]-heads[1][1])*oa[0]
    for dx,dy in ((0,0),(1,0),(-1,0),(0,1)):
        stagger=.7 if name=='ETH RTL port2 TX—J18' else (-.7 if ('port2 RX' in name or 'port1 TX' in name) else 0.)
        stage=[(center[0]+dx+stagger*leg,center[1]+dy+(1 if sign>0 else -1)*leg*.4) for leg in (1,-1)]
        for ribbon in (.74,.86,.9):
            r.rollback(cp);del r.failed[nf:]
            if not all(r.via(stage[i],nets[i],.45,.2) for i in (0,1)):continue
            if not route_pair(r,name,a,b,oa,(-1,0),1.2,2.1 if stagger else 1.2,margin=24,layer=B,
                              endpoints=heads[:2]+stage,ribbon=ribbon,length_bias=bias):continue
            first=r.pairs.pop();first_lengths=first['lengths_mm']
            end_cp=r.checkpoint();finished=False
            choices=[(fo,fe,1.2,eb),((-fo[0],-fo[1]),(-fe[0],-fe[1]),2.1 if stagger else 1.2,
                      3.53 if 'TX' in name and fe==(-1,0) else 2.8)]
            for da,db,ea,ed in choices:
                r.rollback(end_cp)
                shift=(0,-.12) if 'TX' in name and db==(-1,0) else (0,0)
                if route_pair(r,name,a,b,da,db,ea,ed,margin=24,layer=F,
                              endpoints=stage+[r.pos(*p) for p in b],ribbon=ribbon,
                              length_bias=first_lengths,end_shift=shift,
                              end_parallel=([(224 if db==(1,0) else 219,r.pos(*p)[1]) for p in b] if b[0][0] in ('J7','J18') and db in ((1,0),(-1,0)) else ([(201.7,r.pos(*p)[1]) for p in b] if b[0][0]=='T2' and db==(1,0) else None))):
                    finished=True;break
            if not finished:continue
            returns=pair_return_vias(r,stage+getattr(r,'qfn_returns',{}).get(name,[])[:2])
            if returns is None:continue
            pair=r.pairs[-1];pair['layer']='F.Cu/B.Cu';pair['trunk_layer']='B.Cu → F.Cu'
            pair['via_count_per_leg']=2;pair['F_necks']=surface;pair['GND_returns']=returns
            pair['staging_vias_mm']=stage;pair['B_section_lengths_including_source_mm']=first_lengths;pair['preceding_section']=first
            pair['deviation']='B-пара до симметричного перехода в свободной ячейке, затем F; прямой общий коридор перекрыт'
            remove=[]
            secondary=getattr(r,'qfn_returns',{}).get(name,[])[2:]
            for t in r.created:
                if isinstance(t,pcbnew.PCB_VIA) and t.GetNetname() in nets and any(distance(xy(t.GetPosition()),q)<.00001 for q in secondary):remove.append(t.m_Uuid.AsString())
            if b[0][0]=='T2':remove += [u for ref,pin in b for u in r.phy_heads[pin][2]]
            drop_created(r,remove);del r.failed[nf:]
            return True
    r.rollback(cp);del r.failed[nf:];return False


def collapse_qfn_escape(r,name):
    if len(getattr(r,'qfn_returns',{}).get(name,[]))>2:
        secondary=r.qfn_returns[name][2:];ids=[]
        for route in r.done:
            if route['label']==name+' parallel B escape':ids+=route['item_uuids']
        for t in r.created:
            if isinstance(t,pcbnew.PCB_VIA) and any(distance(xy(t.GetPosition()),q)<.00001 for q in secondary):ids.append(t.m_Uuid.AsString())
        drop_created(r,ids)
        first=r.qfn_returns[name][:2];surface=r.bridge_heads[name][2]
        r.bridge_heads[name]=(first,[v['length_mm'] for v in surface],surface)
        r.qfn_returns[name]=first


def bridge_pair(r,name,a,b,oa,ob,is_rj=False):
    """Последний вариант после F.Cu: вся магистраль парой на B, одинаковое
    число .45/.20 via в обоих проводниках и возврат GND у каждого конца.
    Длины учитывают также короткие F-подводы (вертикаль via одинакова).
    """
    collapse_qfn_escape(r,name)
    cp=r.checkpoint();positions=[r.pos(*p) for p in a+b]
    nets=[r.pad(*p).GetNetname() for p in a]
    r.paired.add(frozenset(nets))
    special={
      'ETH W5500 TX—T1':[(190.4,20.2),(191.4,18.5)],
      'ETH RTL port0 RX—T2':[(205.85,38.2),(205.05,38.2)],
      'ETH RTL port1 RX—J7':[(201.2,40.4),(201.2,41.2)],
      'ETH RTL port1 TX—J7':[(201.2,42.8),(201.2,42.0)],
      'ETH RTL port2 TX—J18':[(201.2,45.8),(201.2,46.6)],
      'ETH RTL port2 RX—J18':[(201.7,48.2),(201.7,47.4)],
    }
    cached=getattr(r,"bridge_heads",{}).get(name)
    heads=[];bias=[0.,0.];all_returns=[];surface=[]
    for side,(pair,direction) in enumerate(((a,oa),(b,ob))):
        if side==0 and cached:
            heads=list(cached[0]);bias=list(cached[1]);surface=list(cached[2]);continue
        if side==1 and b[0][0]=='T2' and b[0][1] in getattr(r,'phy_heads',{}):
            for i,pin in enumerate(b):
                q,length,_=r.phy_heads[pin[1]];heads.append(q);bias[i]+=length
                surface.append({'side':1,'leg':i,'length_mm':length})
            continue
        if side==1 and is_rj:
            heads+=positions[2:];continue # PTH RJ45 уже проходят до B.Cu
        pts=positions[side*2:side*2+2]
        if side==0 and name in special:
            candidates=[special[name]]
        else:
            # У H1102 место за длинной стороной площадки; оба отвода равны.
            candidates=[[(p[0]+direction[0]*d,p[1]+direction[1]*d) for p in pts] for d in (1.4,1.7,2.)]
        if side==1 and 'port0 RX' in name:
            candidates=[[(p[0]+1.4,p[1]) for p in pts]] # CT проходит внутри тела, data выходит наружу
        # Веер пары подбирается совместно: фиксированная via-головка могла
        # попасть на питание или соседнюю пару. Шаг .8 сохраняет зазор .20.
        center=tuple((pts[0][i]+pts[1][i])/2 for i in (0,1))
        normal=(-direction[1],direction[0])
        phase=1 if sum((pts[0][i]-pts[1][i])*normal[i] for i in (0,1))>0 else -1
        for d in (1.,1.8,2.6,3.4):
            for shift in (0,-.4,.4,-.8,.8,-1.2,1.2):
                candidates.append([tuple(center[j]+direction[j]*d+normal[j]*(shift+phase*sign*.4) for j in (0,1)) for sign in (1,-1)])
        side_cp=r.checkpoint();selected=None
        for hs in candidates:
            if not all(r.via(q,nets[i],.45,.2) for i,q in enumerate(hs)):
                r.rollback(side_cp);continue
            neck_cp=r.checkpoint();paths={}
            for order in ((0,1),(1,0)):
                paths={};r.rollback(neck_cp)
                for i in order:
                    anchor=pts[i]
                    path=r.search(anchor,hs[i],nets[i],.15,F,margin=3,step=.05)
                    if path is None or not r.track(path,nets[i],.15,F,label=name+' F via neck'):break
                    paths[i]=path
                if len(paths)==2:break
            if len(paths)!=2:r.rollback(side_cp);continue
            paths=[paths[0],paths[1]]
            selected=hs
            for i,path in enumerate(paths):
                length=sum(distance(p,q) for p,q in zip(path,path[1:]));bias[i]+=length
                surface.append({'side':side,'leg':i,'length_mm':length})
            break
        if selected is None:print('bridge head failed',name,side,flush=True);r.rollback(cp);return False
        heads+=selected
    # Возвратные via ставим после B-магистрали: раньше они могли
    # перекрыть её стартовый коридор, хотя рядом оставалось место.

    # Via-головки на B могут выходить в противоположную сторону тела
    # трансформатора: там нет EP. Это устраняет лишние полные обороты пары.
    configs=[(oa,ob,1.2,4.8 if 'port0 TX' in name else 1.8)]
    if is_rj:
        configs=[(oa,ob,1.2,3.53 if 'TX' in name and ob==(1,0) else 2.8)]
    else:configs += [((-oa[0],-oa[1]),(-ob[0],-ob[1]),1.2,1.8)]
    if name=='ETH RTL port0 TX—T2':configs=[((0,1),(-1,0),1.2,1.8)]+configs
    if name=='ETH RTL port0 RX—T2':configs=[((0,1),(1,0),1.2,1.8)]+configs
    def rotated(d,angle):
        c,s=math.cos(angle),math.sin(angle)
        return (round(d[0]*c-d[1]*s,6),round(d[0]*s+d[1]*c,6))
    original=list(configs)
    for da,db,ea,eb in original:
        for aa in (0,-math.pi/4,math.pi/4):
            for ab in ((0,) if is_rj else (0,-math.pi/4,math.pi/4)):
                if aa or ab:configs.append((rotated(da,aa),rotated(db,ab),ea,eb))
    nf=len(r.failed)
    for da,db,ea,eb in configs:
        for width in (.74,.86,.90):
            del r.failed[nf:]
            end_parallel=[(224 if db==(1,0) else 219,positions[i+2][1]) for i in (0,1)] if is_rj and db in ((1,0),(-1,0)) else None
            guides=None
            if name=='ETH RTL port0 TX—T2' and da==(0,1) and db==(-1,0):
                guides=[(201.6,40.8),(201.6,36.0),(196.3,36.0),(196.3,39.175)]
            elif name=='ETH RTL port0 RX—T2' and da==(0,1) and db==(1,0):
                guides=[(207.8,40.9),(210.0,40.9),(210.0,32.825)]
            elif name=='ETH RTL port2 TX—J18' and da==(-1,0) and db==(-1,0):
                guides=[(194.5,45.98),(194.5,30),(216,30),(216,40.56)]
            if route_pair(r,name,a,b,da,db,ea,eb,margin=28,layer=B,endpoints=heads,ribbon=width,
                          length_bias=bias,end_parallel=end_parallel,waypoints=guides):
                returns=pair_return_vias(r,heads)
                if returns is None:
                    raise RuntimeError('Нет возвратной GND via у '+name)
                all_returns+=returns
                entry=r.pairs[-1];entry['layer']='F.Cu/B.Cu';entry['trunk_layer']='B.Cu'
                entry['via_count_per_leg']=1 if is_rj else 2
                entry['F_necks']=surface;entry['GND_returns']=all_returns
                entry['deviation']='B.Cu: F-попытки не прошли проверку; обе линии с одинаковым числом via'
                return True
    if hybrid_pair(r,name,a,b,heads,bias,oa,ob,surface):
        del r.failed[nf:];return True
    print('bridge trunk failed',name,r.failed[nf:],flush=True);del r.failed[nf:];r.rollback(cp);return False


def ethernet_shields(r):
    for j,c,res,dy in [('J7','C112','R115',0),('J18','C114','R118',23)]:
        r.connect((j,8),(c,1),.3,margin=3,label=j+' BS to RC')
        r.connect((c,1),(res,1),.3,margin=3,label=j+' screen RC')
        # Две SH-ножки соединены вдоль корпуса на B, вне сигнальной сетки.
        pads=sorted([p for p in r.fp[j].Pads() if p.GetNumber()=='SH'],key=lambda p:xy(p.GetPosition())[1])
        top,bottom=[xy(p.GetPosition()) for p in pads]
        net=r.pad(j,8).GetNetname()
        paths=[([bottom,(227,bottom[1]-.95),(227,top[1]+.95),top],net),
               ([top,(220.2,top[1]),r.pos(j,8)],net)]
        for pts,net in paths:
            if not r.track(pts,net,.3,B,label=j+' shield B'):
                path=r.search(pts[0],pts[-1],net,.3,B,margin=3)
                if not path or not r.track(path,net,.3,B,label=j+' shield B'):r.failed.append(j+' shield')


def reserve_ethernet_heads(r):
    """Общий веер QFN .4 мм: .55 мм прямо от площадки, затем
    разведение шага .40 → .66 мм. Так соседние выхода не запирают
    питание/MDI; минимум .15/.20 для дорожек и .45/.20 для via.
    """
    r.qfn_heads={};r.bridge_heads={}
    for pin in tuple(range(1,13))+tuple(range(41,49)):
        p=r.pad('U22',pin);a=r.pos('U22',pin);net=p.GetNetname()
        if pin<=12:
            stem=(a[0]-.55,a[1]);q=(200.,44+(a[1]-44)*1.65)
        else:
            stem=(a[0],a[1]-.55);q=(205.2+(a[0]-205.2)*1.65,38.2)
        q=tuple(round(v,6) for v in q)
        if not r.via(q,net,.45,.2):raise RuntimeError('QFN via blocked '+str(pin)+' '+str(q))
        path=[a,stem,q]
        if not r.track(path,net,.15,label='QFN escape '+str(pin)):
            raise RuntimeError('QFN escape blocked '+str(pin))
        r.qfn_heads[pin]=(q,sum(distance(x,y) for x,y in zip(path,path[1:])))
    # LED/RST — после MDI; эти короткие F-выходы оставляют им путь,
    # но длинные B-диагонали заранее не запирают Ethernet-пары.
    r.control_stems={}
    for pin in (27,30,32):
        a=r.pos('U22',pin);q=(a[0]+.55,a[1])
        if not r.track([a,q],r.pad('U22',pin).GetNetname(),.15,label='control stem '+str(pin)):
            raise RuntimeError('control stem blocked '+str(pin))
        r.control_stems[pin]=q
    r.phy_heads={}
    for pin in (1,3,6,8):
        p=r.pos('T2',pin);q=(round(p[0]+1.4,6),p[1]);net=r.pad('T2',pin).GetNetname()
        checkpoint=r.checkpoint()
        if not r.via(q,net,.45,.2) or not r.track([p,q],net,.15,label='PHY reserve T2.'+str(pin)):
            raise RuntimeError('T2 PHY reserve '+str(pin))
        r.phy_heads[pin]=(q,1.4,[o.m_Uuid.AsString() for o in r.created[checkpoint[0]:]])
    for name,pins in [('ETH RTL port0 TX—T2',(47,46)),('ETH RTL port0 RX—T2',(44,45)),
                      ('ETH RTL port1 RX—J7',(2,3)),('ETH RTL port1 TX—J7',(5,4)),
                      ('ETH RTL port2 TX—J18',(9,10)),('ETH RTL port2 RX—J18',(12,11))]:
        heads=[r.qfn_heads[n][0] for n in pins];bias=[r.qfn_heads[n][1] for n in pins]
        # Последний резерв в плотном веере: параллельный B-переход
        # выносит обе линии за поле QFN, затем основная пара вновь на F.
        target=[(q[0],35.2) if pins[0]>12 else (196.5,q[1]) for q in heads]
        for i in (0,1):
            net=r.pad('U22',pins[i]).GetNetname()
            if not r.via(target[i],net,.45,.2):raise RuntimeError('QFN second via '+name)
            if not r.track([heads[i],target[i]],net,.24,B,label=name+' parallel B escape'):
                raise RuntimeError('QFN B escape '+name)
        surface=[{'side':0,'leg':i,'length_mm':bias[i]} for i in (0,1)]
        total=[bias[i]+distance(heads[i],target[i]) for i in (0,1)]
        r.bridge_heads[name]=(target,total,surface)
        if not hasattr(r,'qfn_returns'):r.qfn_returns={}
        r.qfn_returns[name]=heads+target


def ethernet(r):
    # out_b может смотреть внутрь трансформатора: под ним нет EP, в отличие
    # от U22. Это позволяет сохранить полярность без перекреста/слоя B.
    tasks=[
      ('ETH W5500 RX—C64/C65',[('U10',6),('U10',5)],[('C64',1),('C65',1)],(-1,0),(1,0),1.4,.65),
      ('ETH C64/C65—T1',[('C64',2),('C65',2)],[('T1',6),('T1',8)],(-1,0),(0,1),1.2,4.8),
      ('ETH W5500 TX—T1', [('U10',2),('U10',1)], [('T1',1),('T1',3)],(-1,0),(0,1),1.4,4.8),
      ('ETH LNK_A T1—T2',[('T1',16),('T1',14)],[('T2',11),('T2',9)],(0,-1),(1,0),1.8,1.8),
      ('ETH LNK_B T1—T2',[('T1',11),('T1',9)],[('T2',16),('T2',14)],(0,-1),(1,0),1.8,1.8),
      ('ETH RTL port0 TX—T2',[('U22',47),('U22',46)],[('T2',1),('T2',3)],(0,-1),(1,0),1.05,1.8),
      ('ETH RTL port0 RX—T2',[('U22',44),('U22',45)],[('T2',6),('T2',8)],(0,-1),(-1,0),1.05,2.2),
      ('ETH RTL port1 RX—J7',[('U22',2),('U22',3)],[('J7',1),('J7',2)],(-1,0),(-1,0),1.3,2.8),
      ('ETH RTL port1 TX—J7',[('U22',5),('U22',4)],[('J7',3),('J7',6)],(-1,0),(1,0),1.3,3.0),
      ('ETH RTL port2 RX—J18',[('U22',12),('U22',11)],[('J18',1),('J18',2)],(-1,0),(1,0),1.3,2.8),
      ('ETH RTL port2 TX—J18',[('U22',9),('U22',10)],[('J18',3),('J18',6)],(-1,0),(-1,0),1.3,2.8),
    ]
    # Резервируем короткую CT/bias-ячейку до магистралей, иначе fanout
    # занимал соединение между RCT и общими выводами R51/R52.
    for x,y in [(('T1',2),('C63',1)),                (('T1',7),('C66',1)),(('C66',1),('R51',2)),(('C66',1),('R52',1)),
                (('T1',6),('R51',1)),(('T1',8),('R52',2)),
                (('J7',4),('J7',5)),(('J7',4),('C67',1)),
                (('J18',4),('J18',5)),(('J18',4),('C109',1))]:
        r.connect(x,y,.24 if x in (('T1',6),('T1',8)) else .2,margin=4,step=.1)
    if not r.track([r.pos('T2',2),(196.7,39.175),(196.7,32.825),r.pos('T2',7)],r.pad('T2',2).GetNetname(),.2,label='T2 CT inside body'):r.failed.append('T2 CT inside body')
    kelvin(r,('T1',2),('R50',2),.2,.45,.2,source_via=(176.825,38.8))
    r.connect(('T2',7),('C85',1),.2,margin=2,label='T2 RCT to C85')
    kelvin(r,('U10',2),('R48',1),.2,.45,.2,source_via=(193.4,19.75))
    kelvin(r,('U10',1),('R49',1),.2,.45,.2,source_via=(192.7,19.0))
    ethernet_shields(r)
    missing=[]
    for name,a,b,oa,ob,ea,eb in tasks:
        errors=len(r.failed);ok=False
        if name in getattr(r,'bridge_heads',{}):
            h,bias,surface=r.bridge_heads[name]
            endpoints=h+[r.pos(*p) for p in b]
            configs=[(oa,ob,1.2,eb),((-oa[0],-oa[1]),(-ob[0],-ob[1]),1.2,2.2 if b[0][0]=='T2' else 1.8)]
            for da,db,ex,ey in configs:
                for width in (.74,.86,.90):
                    del r.failed[errors:]
                    parallel=[(224 if db==(1,0) else 219,r.pos(*p)[1]) for p in b] if b[0][0] in ('J7','J18') and db in ((1,0),(-1,0)) else None
                    shift=(0,-.12) if b[0][0] in ('J7','J18') and 'TX' in name and db==(-1,0) else (0,0)
                    if route_pair(r,name,a,b,da,db,ex,ey,margin=32,ribbon=width,endpoints=endpoints,length_bias=bias,end_parallel=parallel,end_shift=shift):
                        ok=True;break
                if ok:break
            del r.failed[errors:]
            if ok:
                entry=r.pairs[-1];entry['F_necks']=surface
                entry['layer']='F.Cu/B.Cu';entry['trunk_layer']='F.Cu';entry['via_count_per_leg']=2
                entry['GND_returns']=pair_return_vias(r,r.qfn_returns[name])
                entry['deviation']='Параллельный выход QFN на B.Cu, основная пара F.Cu'
                if b[0][0]=='T2':
                    remove={u for ref,pin in b for u in r.phy_heads[pin][2]}
                    for t in list(r.created):
                        if t.m_Uuid.AsString() in remove:
                            r.group.RemoveItem(t);r.board.Remove(t);r.created.remove(t)
                    r.done[:]=[route for route in r.done if not any(u in remove for u in route['item_uuids'])]
                    r.rollback(r.checkpoint())
            else:missing.append((name,a,b,oa,ob))
            continue
        orientations=[(oa,ob)]
        if a[0][0] in ('T1','T2'):
            orientations.append(((-oa[0],-oa[1]),(-ob[0],-ob[1])))
        for da,db in orientations:
            for width in (.74,.80,.86,.90):
                del r.failed[errors:]
                receiver=name=='ETH C64/C65—T1';transmitter=name=='ETH W5500 TX—T1'
                target=[('R51',1),('R52',2)] if receiver else b
                bias=[next(v['length_mm'] for v in r.done if v['label']==label) for label in ('T1.6—R51.1','T1.8—R52.2')] if receiver else [0.,0.]
                end_y=48.0 if receiver else 45.225
                parallel=[(r.pos(*p)[0],end_y) for p in target] if receiver or transmitter else None
                ok=route_pair(r,name,a,target,da,db,ea,(end_y-r.pos(*target[0])[1]) if parallel else eb,ribbon=width,
                              margin=32 if ('port1' in name or 'port2' in name) else 12,
                              heading_a=None,
                              heading_b=(0,-1) if name=='ETH RTL port2 TX—J18' else None,
                              waypoints=[(182.8,27),(186.6,28),(187.2,49),(183.175,49)] if receiver else None,
                              end_parallel=parallel,length_bias=bias)
                if ok and receiver:r.pairs[-1]['fixed_end_lengths_mm']=bias
                if ok:break
            if ok:break
        del r.failed[errors:]
        if not ok:missing.append((name,a,b,oa,ob))
    # Внешняя верхняя дуга TX2 — первой. Остальные B-пары остаются
    # по свою сторону этой дуги, не запирая друг другу выводы.
    priority={'ETH RTL port2 TX—J18':0,'ETH LNK_A T1—T2':1,'ETH LNK_B T1—T2':2,
              'ETH RTL port0 TX—T2':3,'ETH RTL port0 RX—T2':4,
              'ETH RTL port2 RX—J18':5,'ETH W5500 TX—T1':6}
    missing.sort(key=lambda task:priority.get(task[0],7))
    for name,a,b,oa,ob in missing:collapse_qfn_escape(r,name)
    for name,a,b,oa,ob in missing:
        if not bridge_pair(r,name,a,b,oa,ob,is_rj=b[0][0] in ('J7','J18')):
            r.failed.append(name+' (F/B не пройдены)')
    for pair in r.pairs:
        if pair.get('trunk_layer')=='B.Cu' and pair['name'] in getattr(r,'qfn_returns',{}):
            secondary=r.qfn_returns[pair['name']][2:]
            for t in list(r.created):
                if isinstance(t,pcbnew.PCB_VIA) and t.GetNetname() in pair['nets'] and any(distance(xy(t.GetPosition()),q)<.00001 for q in secondary):
                    r.group.RemoveItem(t);r.board.Remove(t);r.created.remove(t)
            pair['GND_returns']=(pair.get('GND_returns') or [])+(pair_return_vias(r,r.qfn_returns[pair['name']][:2]) or [])
    r.rollback(r.checkpoint())


def thermal(r):
    # Тепловой массив — ДО любой B-трассы. Иначе поиск служебных цепей
    # занимал места отверстий под EP и часть массива молча не помещалась.
    cx,cy=xy(r.fp['U22'].GetPosition())
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            if not r.via((cx+dx,cy+dy),'GND',.45,.2):
                raise RuntimeError('не помещается тепловой массив 3x3 U22')
    r.copper('GND',(cx-2.2,cy-2.2,cx+2.2,cy+2.2),B,name='U22:EP49')


def ground(r):
    for ref in ('Y1','Y2','Y3'):
        x,y=xy(r.fp[ref].GetPosition())
        for dx,dy in ((-2.5,-2),(2.5,-2),(-2.5,2),(2.5,2)):
            r.via((x+dx,y+dy))
    # Швы кромок через 8 мм. Если номинальная точка занята площадкой,
    # смещаемся ПО НОРМАЛИ к кромке (а не пропускаем точку и оставляем
    # 16–24 мм). Разброс до 5,2 мм всё ещё даёт расстояние <10 мм.
    recipes=[('top',range(8,236,8),(1.2,.8,2.,3.,4.,5.,6.)),
             ('bottom',range(8,236,8),(118.8,119.2,118.,117.,116.,115.,114.)),
             ('left',range(8,116,8),(1.2,.8,2.,3.,4.,5.,6.)),
             ('right',range(8,116,8),(238.8,239.2,238.,237.,236.,235.,234.))]
    for edge,along,normals in recipes:
        for a in along:
            candidates=[(a,n) if edge in ('top','bottom') else (n,a) for n in normals]
            if edge=='right' and a==104:
                # Ряд полевых клемм перекрывает нормаль y=104. Вне отверстий
                # остаётся (239.2,105); до соседей 9.01/7.02 мм, зазор до края .5.
                candidates.append((239.2,105))
            for q in candidates:
                if r.via(q):
                    r.edge_stitches.append({'edge':edge,'at_mm':q});break
            else:r.failed.append('GND stitching %s %s'%(edge,a))
    # Возврат каждой локальной земли в сплошной In1. Via за краем SMD,
    # не в паяемой площадке 0603. ETH_SH* сюда не попадает по имени цепи.
    for f in sorted(r.fp.values(),key=lambda f:f.GetReference()):
        for p in sorted(f.Pads(),key=lambda p:(p.GetNumber(),xy(p.GetPosition()))):
            if p.GetNetname()!='GND' or p.GetDrillSize().x or not p.IsOnLayer(F):continue
            # Большие EP у U1/U7 уже имеют PTH; U22 обработан отдельным массивом.
            if f.GetReference() in ('U1','U7','U22') and p.GetNumber() in ('21','49'):continue
            x,y=xy(p.GetPosition()); box=p.GetBoundingBox()
            halfx,halfy=pcbnew.ToMM(box.GetWidth())/2,pcbnew.ToMM(box.GetHeight())/2
            choices=[(x+halfx+.4,y),(x-halfx-.4,y),(x,y+halfy+.4),(x,y-halfy-.4)]
            if f.GetReference().startswith('U'):
                fx,fy=xy(f.GetPosition())
                choices.sort(key=lambda q:-distance(q,(fx,fy)))
            for q in choices:
                if r.free((x,y),q,.2,'GND') and r.via(q):
                    r.track([(x,y),q],'GND',.2,label='GND '+f.GetReference()+'.'+p.GetNumber())
                    break


def back_pad(r, refpin):
    """SMD-площадка → via за краем площадки, без via-in-pad 0603."""
    p=r.pad(*refpin);net=p.GetNetname();x,y=xy(p.GetPosition())
    bb=p.GetBoundingBox();hx=pcbnew.ToMM(bb.GetWidth())/2;hy=pcbnew.ToMM(bb.GetHeight())/2
    for gap in (.3,.55,.85,1.2):
        for q in [(x-hx-gap,y),(x+hx+gap,y),(x,y-hy-gap),(x,y+hy+gap)]:
            if r.free((x,y),q,.2,net) and r.canvia(q,net,.45,.2):
                r.via(q,net,.45,.2);r.track([(x,y),q],net,.2,label='back '+str(refpin));return q
    return None


def tree_join(r,start,root,net,layer,width,label):
    """Ближайшая ветвь и перпендикулярное T, без острых пересечений.
    При поиске подхода своя существующая медь тоже препятствие; только
    последний прямой отрезок присоединяется к выбранной ветви.
    """
    candidates=[]
    for t in r.board.GetTracks():
        if isinstance(t,pcbnew.PCB_VIA) or t.GetLayer()!=layer or t.GetNetname()!=net:continue
        a,b=xy(t.GetStart()),xy(t.GetEnd());length=distance(a,b)
        if length<.8:continue
        vx,vy=(b[0]-a[0])/length,(b[1]-a[1])/length
        along=max(.4,min(length-.4,(start[0]-a[0])*vx+(start[1]-a[1])*vy))
        p=(a[0]+vx*along,a[1]+vy*along)
        if distance(start,p)<pcbnew.ToMM(t.GetWidth())/2+.215:return True
        nx,ny=-vy,vx;side=1 if (start[0]-p[0])*nx+(start[1]-p[1])*ny>=0 else -1
        for gap in (.8,1.2):
            lead=(p[0]+nx*side*gap,p[1]+ny*side*gap)
            candidates.append((distance(start,p),lead,p))
    for _,lead,p in sorted(candidates)[:8]:
        r.block_own=(net,layer)
        path=r.search(start,lead,net,width,layer,margin=3,step=.2,max_nodes=20000)
        r.block_own=None
        if path is None or not simple_path(path+[p]):continue
        if r.track(path+[p],net,width,layer,label=label):return True
    path=r.search(start,root,net,width,layer,margin=6,step=.1)
    return bool(path and simple_path(path) and r.track(path,net,width,layer,label=label))


def vdd_bridge(r,pins=(18,31)):
    # Via VDD18/31 могли остаться на островках +3V3 In2. Новый via выбирается
    # НА ОСНОВНОЙ заполненной области питания, а не по одному имени net.
    zones=[z for z in r.board.Zones() if not z.GetIsRuleArea() and z.IsOnLayer(pcbnew.In2_Cu) and z.GetNetname()=='+3V3']
    areas=[]
    for z in zones:
        poly=z.GetFilledPolysList(pcbnew.In2_Cu)
        for i in range(poly.OutlineCount()):areas.append((abs(poly.COutline(i).Area()),poly,i))
    _,poly,i=max(areas,key=lambda value:value[0]);parent=pcbnew.SHAPE_POLY_SET()
    parent.AddOutline(poly.COutline(i))
    for j in range(poly.HoleCount(i)):parent.AddHole(poly.CHole(i,j))
    routes={v['label']:v for v in r.done};net='+3V3'
    targets={18:('R113',1),31:('C99',1)}
    def escape(source,pin):
        # На противоположной стороне корпуса может быть свободнее, чем
        # на F между развязкой и LED. Via проверяется на всех слоях.
        candidates=[(dx*.5,dy*.5) for dx in range(-12,13) for dy in range(-12,13) if 1<=dx*dx+dy*dy<=144]
        for dx,dy in sorted(candidates,key=lambda v:(v[0]*v[0]+v[1]*v[1],v)):
            q=(source[0]+dx,source[1]+dy)
            if not parent.Collide(point(q),0) or not r.canvia(q,net,.45,.2):continue
            for layer in (B,F):
                path=r.search(source,q,net,.2,layer,margin=4,step=.1,max_nodes=30000)
                if path is None:continue
                cp=r.checkpoint()
                if r.via(q,net,.45,.2) and r.track(path,net,.2,layer,label='U22 VDD island escape '+str(pin)):return True
                r.rollback(cp)
        return False
    for pin in pins:
        source=routes['fanout U22.'+str(pin)]['end_mm'];pad=r.pos(*targets[pin])
        connected=any(isinstance(v,pcbnew.PCB_VIA) and v.GetNetname()==net and distance(xy(v.GetPosition()),source)<.00001
                      and parent.Collide(v.GetEffectiveShape(pcbnew.In2_Cu),2) for v in r.board.GetTracks())
        if connected:continue
        lead=r.search(source,pad,net,.2,F,margin=3,step=.05)
        if lead is None:
            if not escape(source,pin):r.failed.append('VDD lead '+str(pin))
            continue
        found=False
        for radius in (.8,1.1,1.5,2.,2.5,3.):
            for dx,dy in ((-1,0),(1,0),(0,1),(0,-1),(-1,1),(1,1),(-1,-1),(1,-1)):
                q=(pad[0]+dx*radius,pad[1]+dy*radius)
                if not parent.Collide(point(q),0) or not r.canvia(q,net,.45,.2):continue
                path=r.search(pad,q,net,.2,F,margin=2,step=.05)
                if path is None:continue
                cp=r.checkpoint()
                if r.via(q,net,.45,.2) and r.track(lead,net,.2,F,label='U22 VDD lead '+str(pin)) and r.track(path,net,.2,F,label='U22 VDD parent via '+str(pin)):
                    found=True;break
                r.rollback(cp)
            if found:break
        if not found and not escape(source,pin):r.failed.append('VDD parent plane via '+str(pin))


def core_inner(r):
    """VCORE — питание, ручное дерево In2; In1/GND не разрезается.
    На B сигналы могли разрезать остров VCORE на несвязанные камеры.
    Узкое дерево In2 соединяет все core-via, сохраняя остальную +3V3-заливку.
    """
    net='SW_VCORE';vias=[v for v in r.created if isinstance(v,pcbnew.PCB_VIA) and v.GetNetname()==net]
    root=min(vias,key=lambda v:distance(xy(v.GetPosition()),r.pos('C87',1)))
    root=xy(root.GetPosition())
    for via in sorted(vias,key=lambda v:(distance(xy(v.GetPosition()),root),xy(v.GetPosition()))):
        q=xy(via.GetPosition())
        if distance(q,root)<.00001:continue
        if not tree_join(r,q,root,net,pcbnew.In2_Cu,.3,'CORE In2 tree'):r.failed.append('CORE In2 '+str(q))


def sense_branch(r,source,net):
    q=back_pad(r,source)
    tracks=[t for t in r.board.GetTracks() if not isinstance(t,pcbnew.PCB_VIA) and t.GetLayer()==B and t.GetNetname()==net]
    root=xy(tracks[0].GetStart()) if tracks else None
    if not q or not root or not tree_join(r,q,root,net,B,.2,'VOUT sense branch '+str(source)):
        r.failed.append('VOUT sense branch '+str(source))


def fanout(r,controls=False):
    """Смещённые via служебных выводов U22 с ЗАВЕРШЁННЫМ подводом B.

    3V3 попадает в In2; VCORE не соединяется с 3V3. MDI/кварц на F.
    """
    cx,cy=xy(r.fp['U22'].GetPosition())
    mdi=set(range(2,6))|set(range(9,13))|set(range(44,48))|{39,40,49}
    target={'SW_VCORE':('C87',1),'SW_RST':('R113',2),'SW_IBREF':('R112',1),
            'SW_LED1':('R54',1),'SW_LED2':('R114',1)}
    backs={}
    for p in sorted(r.fp['U22'].Pads(),key=lambda p:(0 if p.GetNumber() in ('27','30','32','42') else 1,int(p.GetNumber()) if p.GetNumber() else 0)):
        if not p.GetNetname() or not p.GetNumber() or int(p.GetNumber()) in mdi:continue
        is_control=p.GetNumber() in ('27','30','32')
        if is_control!=controls:continue
        if int(p.GetNumber()) in getattr(r,'qfn_heads',{}):
            if p.GetNumber()=='42':
                q=r.qfn_heads[42][0];dest=back_pad(r,('R112',1));net=p.GetNetname()
                path=r.search(q,dest,net,.2,B,margin=4) if dest else None
                if not path or not r.track(path,net,.2,B,label='QFN IBREF to R112'):r.failed.append('QFN IBREF')
            continue
        if p.GetNumber()=='38':
            if r.track([r.pos('U22',38),r.pos('U22',37)],p.GetNetname(),.15,label='VDD 38—37'):continue
        x,y=xy(p.GetPosition());dx,dy=x-cx,y-cy
        sign=1 if (dx if abs(dx)>abs(dy) else dy)>0 else -1
        cp=r.checkpoint();net=p.GetNetname();short=net.split('/')[-1]
        if p.GetNumber()=='41':
            # Один общий VCORE via с pin43: отдельный переход у 41 не
            # помещается между кварцем и IBREF при кольце 0,125 мм.
            path=r.search((x,y),r.pos('U22',43),net,.15,margin=3,step=.05)
            if path and r.track(path,net,.15,label='CORE U22.41—43'):continue
        anchor=getattr(r,'control_stems',{}).get(int(p.GetNumber()),(x,y))
        q=None;stem=None
        if p.GetNumber()=='31':
            # Via снаружи внутреннего VCORE-дерева: старое (209.925,43.8)
            # попадало на изолированный остров +3V3. Рядом вход C99.
            candidate=(211.0,43.8)
            path=r.search(anchor,candidate,net,.15,margin=2,step=.05)
            if r.canvia(candidate,net,.45,.2) and path:q,stem=candidate,path
        # Via требует шага больше 0,4 мм; кроме двух радиусов раздвигаем
        # окончания вдоль ряда. Прямое чередование без веера давало бы
        # clearance .10 мм между via и соседним длинным стволом.
        radii=(1.,1.8,2.6,3.4,.4,.6,4.2) if int(p.GetNumber())%2 else (1.8,1.,2.6,3.4,.4,.6,4.2)
        north={
            41:((206.4,39.3),[(206.6,41.075),(206.6,39.8),(206.4,39.3)]),
            42:((206.09,40.2),[(206.2,41.075),(206.2,40.8),(206.09,40.2)]),
            43:((205.4,39.3),[(205.8,41.075),(205.8,40.7),(205.4,39.9),(205.4,39.3)]),
        }
        # Переход IBREF близко к своему выводу, CORE расходятся по обе стороны;
        # все три помещаются между рядом .4 мм и трассами кварца без перекрёста.
        if int(p.GetNumber()) in north and anchor==(x,y):
            candidate,path=north[int(p.GetNumber())]
            if r.canvia(candidate,net,.45,.2) and all(r.free(a,b,.15,net) for a,b in zip(path,path[1:])):
                q,stem=candidate,path
        for radius in radii:
            if is_control and radius<.8:continue
            if q is not None:break
            tangents={6:(-.8,),8:(.8,)}.get(int(p.GetNumber()),())+(0,-.4,.4,-.8,.8,-1.2,1.2,-1.6,1.6,-2.,2.)
            for tangent in tangents:
                candidate=(x+sign*radius,y+tangent) if abs(dx)>abs(dy) else (x+tangent,y+sign*radius)
                if not r.canvia(candidate,net,.45,.2):continue
                path=r.search(anchor,candidate,net,.15,margin=3,step=.05)
                if path is not None:q,stem=candidate,path;break
            if q is not None:break
        if q is None:
            r.failed.append('fanout U22.'+p.GetNumber());continue
        r.via(q,net,.45,.2)
        r.track(stem,net,.15,label='fanout U22.'+p.GetNumber())
        if net=='+3V3':continue
        if short not in target:
            r.rollback(cp);r.failed.append('fanout target '+short);continue
        key=target[short]
        dest=backs.get(key)
        if dest is None:
            dest=back_pad(r,key)
        if net=='SW_VCORE':
            ok=bool(dest) # все CORE via соединяются в core_inner() после MDI
        else:
            path=r.search(q,dest,net,.2,B,margin=5) if dest else None
            ok=bool(path and r.track(path,net,.2,B,label='fanout to '+str(key)))
        if not ok:
            r.rollback(cp)
            # LED/RST малоточные: обход на F, если B пересечён MDI-парой.
            path=r.search(anchor,r.pos(*key),net,.15,F,margin=14,step=.1,max_nodes=160000) if is_control else None
            if path and r.track(path,net,.15,F,label='control F U22.'+p.GetNumber()):continue
            r.failed.append('fanout B/F U22.'+p.GetNumber());continue
        backs[key]=dest
    # Все накопительные/развязывающие ёмкости ядра в ту же сеть B.Cu.
    for key in ([('C106',1)] if controls else [('C'+str(i),1) for i in range(86,97)]):
        short=r.pad(*key).GetNetname().split('/')[-1]
        master=target[short]
        if key==master:continue
        cp=r.checkpoint();a=back_pad(r,key);b=backs.get(master)
        if b is None:b=back_pad(r,master)
        net=r.pad(*key).GetNetname()
        if net=='SW_VCORE':
            ok=bool(a and b) # физическая связь — последующее дерево core_inner()
        else:
            path=r.search(a,b,net,.3,B,margin=5) if a and b else None
            ok=bool(path and r.track(path,net,.3,B,label='RTL decoupling '+key[0]))
        if not ok:
            r.rollback(cp)
            if controls:
                path=r.search(r.pos(*key),r.pos(*master),net,.2,F,margin=10,step=.1)
                if path and r.track(path,net,.2,F,label='reset capacitor F'):continue
            r.failed.append('RTL decoupling '+key[0]);continue
        backs[master]=b


def main(path):
    board=pcb_route.load(path)
    if any(g.GetName()==TAG for g in board.Groups()):
        raise SystemExit('pcb_preroute: уже выполнено; повторите pcb_build → init на свежей плате')
    if any(t for t in board.GetTracks()):
        raise SystemExit('pcb_preroute: ожидается свежая плата без дорожек')
    expected={'U1':(34,84),'U2':(68,12),'U3':(68,40),'U4':(68,68),
              'U5':(46,26),'U6':(46,56),'U10':(196,22),'U22':(206,44),'Y3':(211,36),
              'T1':(180,36),'T2':(193.5,36),'J7':(222.74,22),'J18':(222.74,45)}
    fp={f.GetReference():f for f in board.GetFootprints()}
    for ref,pos in expected.items():
        if ref not in fp or distance(xy(fp[ref].GetPosition()),pos)>.001:
            raise SystemExit('pcb_preroute: обновите координатные рецепты после смещения '+ref)
    pcbnew.KIID.SeedGenerator(73474)
    r=Router(board)
    thermal(r)
    power(r)
    usb(r)
    reserve_ethernet_heads(r)
    clocks(r)
    fanout(r)
    ethernet(r)
    fanout(r,controls=True)
    core_inner(r)
    ground(r)
    eth=[p for p in r.pairs if p['name'].startswith('ETH ')]
    if len(eth)!=11 or len({p['name'] for p in eth})!=11:r.failed.append('требуются все 11 Ethernet-пар')
    for pair in eth:
        for section in [pair]+([pair['preceding_section']] if 'preceding_section' in pair else []):
            if any(v>3.0001 for fan in section.get('unpaired_fanout_lengths_mm',[]) for v in fan):
                r.failed.append('fanout >3 мм: '+pair['name'])
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    vdd_bridge(r)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcb_route.save(board,path)
    manifest={'schema':1,'created':len(r.created),'tracks':len([o for o in r.created if isinstance(o,pcbnew.PCB_TRACK) and not isinstance(o,pcbnew.PCB_VIA)]),
              'vias':len([o for o in r.created if isinstance(o,pcbnew.PCB_VIA)]),'edge_stitches':r.edge_stitches,'pairs':r.pairs,'routes':r.done,'not_routed':r.failed}
    with open(os.path.splitext(path)[0]+'.preroute.json','w',encoding='utf-8') as f:
        json.dump(manifest,f,ensure_ascii=False,indent=2);f.write('\n')
    print('preroute: закреплено %d объектов; не выполнено %d локальных соединений' % (len(r.created),len(r.failed)))
    if r.failed:
        raise SystemExit('pcb_preroute: неполный результат, см. .preroute.json; автотрассировка остановлена')


if __name__=='__main__':
    main(sys.argv[1])
