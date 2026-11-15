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
                for layer in (F, B):
                    if p.IsOnLayer(layer):
                        self.obstacle(p, layer)
        for t in board.GetTracks():
            for layer in (F, B):
                if t.IsOnLayer(layer):
                    self.obstacle(t, layer)

    def checkpoint(self):
        return len(self.created),len(self.done),self.serial

    def rollback(self, checkpoint):
        count,done,serial=checkpoint
        for obj in self.created[count:]:
            self.group.RemoveItem(obj)
            self.board.Remove(obj)
        del self.created[count:];del self.done[done:];self.serial=serial
        self.index.clear()
        for f in sorted(self.board.GetFootprints(),key=lambda f:f.GetReference()):
            for p in f.Pads():
                for layer in (F,B):
                    if p.IsOnLayer(layer):self.obstacle(p,layer)
        for t in self.board.GetTracks():
            for layer in (F,B):
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
                    if other == net or other in ignore or id(obj) in seen:
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

    def search(self, start, goal, net, width, layer=F, margin=2, step=.1, ignore=(), gate=None):
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
        def coord(n):
            return round(n[0] * step, 6), round(n[1] * step, 6)
        s = tuple(round(v / step) for v in start)
        g = tuple(round(v / step) for v in goal)
        if not self.free(start, coord(s), width, net, layer, ignore) or not self.free(coord(g), goal, width, net, layer, ignore):
            return None
        queue = [(distance(coord(s), goal), 0., s)]
        cost, parent = {s: 0.}, {}
        visited = 0
        directions = ((1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1))
        while queue:
            _, d, n = heapq.heappop(queue)
            if d > cost[n] + 1e-8:
                continue
            if n == g:
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
            if visited > 80000:
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
        if any(not self.free(pos, pos, diameter, net, layer) for layer in (F, B)):
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
        self.obstacle(v, F); self.obstacle(v, B)
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
        kelvin(r, (u,1), (cout[0],1), .2)
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
    q=(85.3,79.6);start=r.pos('L3',2)
    route=r.search(start,q,'+3V3',1.5,margin=3)
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
        if u=='U22':
            # XI не режет по диагонали поле CORE/IBREF: вертикальный выход
            # оставляет слева коридор для их веера. XO обходит землю кварца.
            paths=[([(207,41.075),(207,38.5),(204.9,38.5),r.pos(y,1)],yi),
                   ([(207.4,41.075),(207.4,40),(208.3,38.9),(208.3,35.65),r.pos(y,3)],yo)]
            for pts,pin in paths:
                if not r.track(pts,r.pad(u,pin).GetNetname(),.15,label=u+' crystal '+str(pin)):
                    r.failed.append(u+' crystal '+str(pin))
        else:r.connect((u,yi),(y,1),.15,margin=2,step=.05)
        if u!='U22':r.connect((u,yo),(y,3 if y!='Y2' else 2),.15,margin=2,step=.05)
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


def route_pair(r,name,a,b,out_a,out_b,escape_a=1.4,escape_b=1.8,margin=8):
    """Совместный коридор 0,68 мм, затем две offset-линии 0,24/0,20.

    Последние миллиметры у выводов — fanout 0,15 мм (шаг QFN 0,4).
    Никаких двух независимо найденных длинных линий под видом пары.
    """
    pads=[r.pad(*p) for p in a+b]
    if pads[0].GetNetname()!=pads[2].GetNetname() or pads[1].GetNetname()!=pads[3].GetNetname():
        raise ValueError('не совпали сети пары '+name)
    nets=[pads[0].GetNetname(),pads[1].GetNetname()]
    r.paired.add(frozenset(nets))
    positions=[xy(p.GetPosition()) for p in pads]
    mean_a=tuple((positions[0][i]+positions[1][i])/2 for i in (0,1))
    mean_b=tuple((positions[2][i]+positions[3][i])/2 for i in (0,1))
    ca=tuple(mean_a[i]+out_a[i]*escape_a for i in (0,1))
    cb=tuple(mean_b[i]+out_b[i]*escape_b for i in (0,1))
    sign_a=(positions[0][0]-positions[1][0])*(-out_a[1])+(positions[0][1]-positions[1][1])*out_a[0]
    sign_b=(positions[2][0]-positions[3][0])*out_b[1]-(positions[2][1]-positions[3][1])*out_b[0]
    if sign_a*sign_b<=0:
        raise ValueError('инверсия порядка проводников '+name)
    delta=.22 if sign_a>0 else -.22
    sa=tuple(ca[i]+out_a[i]*.6 for i in (0,1))
    sb=tuple(cb[i]+out_b[i]*.6 for i in (0,1))
    route=r.search(sa,sb,nets[0],.90,margin=margin,step=.1,ignore=nets,gate=(out_a,out_b))
    if route is None:
        r.failed.append(name+' (нет общего коридора)');return False
    center=[ca]+route+[cb]
    try:middle=[offset(center,delta),offset(center,-delta)]
    except ValueError:
        r.failed.append(name+' (разворот коридора)');return False
    # Транзакция: если соседний проводник не проходит — не оставлять первый.
    cp=r.checkpoint();sections=[]
    for i in (0,1):
        start=r.search(positions[i],middle[i][0],nets[i],.15,margin=2,step=.05)
        end=r.search(middle[i][-1],positions[i+2],nets[i],.15,margin=2,step=.05)
        if start is None or end is None:
            r.rollback(cp);r.failed.append(name+' (fanout)');return False
        pieces=[(start,.15),(middle[i],.24),(end,.15)]
        if not all(r.track(p,nets[i],w,label=name) for p,w in pieces):
            r.rollback(cp);r.failed.append(name+' (offset/clearance)');return False
        sections.append(pieces)
    r.rollback(cp)
    lengths=[sum(distance(a,b) for p,w in pieces for a,b in zip(p,p[1:])) for pieces in sections]
    # Компенсация только в uncoupled fanout: основную пару не раздвигаем.
    attempts=[sections]
    diff=abs(lengths[0]-lengths[1])
    if diff>.5:
        short=0 if lengths[0]<lengths[1] else 1
        attempts=[]
        for section in (0,2):
            pts=sections[short][section][0]
            for j,(a0,b0) in enumerate(zip(pts,pts[1:])):
                length=distance(a0,b0)
                if length<.4:continue
                height=math.sqrt(diff*(2*length+diff))/2
                if height>2:continue
                for sign in (-1,1):
                    peak=((a0[0]+b0[0])/2-sign*(b0[1]-a0[1])/length*height,
                          (a0[1]+b0[1])/2+sign*(b0[0]-a0[0])/length*height)
                    new=[[(list(p),w) for p,w in pieces] for pieces in sections]
                    new[short][section]=(pts[:j+1]+[peak]+pts[j+1:],.15)
                    attempts.append(new)
    for candidate in attempts:
        ok=True
        for i in (0,1):
            for pts,w in candidate[i]:
                if not r.track(pts,nets[i],w,label=name):ok=False;break
            if not ok:break
        if ok:
            ls=[sum(distance(a,b) for p,w in pieces for a,b in zip(p,p[1:])) for pieces in candidate]
            r.pairs.append({'name':name,'nets':nets,'layer':'F.Cu','width_mm':.24,'gap_mm':.2,
                            'fanout_width_mm':.15,'lengths_mm':[round(v,6) for v in ls],
                            'skew_mm':round(abs(ls[0]-ls[1]),6)})
            print('пара:',name,ls,flush=True);return True
        r.rollback(cp)
    r.failed.append(name+' (согласование длины/зазор)');return False


def ethernet(r):
    # out_b может смотреть внутрь трансформатора: под ним нет EP, в отличие
    # от U22. Это позволяет сохранить полярность без перекреста/слоя B.
    tasks=[
      ('ETH W5500 TX—T1', [('U10',2),('U10',1)], [('T1',1),('T1',3)],(-1,0),(0,-1),1.4,1.8),
      ('ETH W5500 RX—C64/C65',[('U10',6),('U10',5)],[('C64',1),('C65',1)],(-1,0),(1,0),1.4,1.2),
      ('ETH C64/C65—T1',[('C64',2),('C65',2)],[('T1',6),('T1',8)],(-1,0),(0,-1),1.2,1.8),
      ('ETH LNK_A T1—T2',[('T1',16),('T1',14)],[('T2',11),('T2',9)],(0,1),(0,1),1.8,1.8),
      ('ETH LNK_B T1—T2',[('T1',11),('T1',9)],[('T2',16),('T2',14)],(0,1),(0,1),1.8,1.8),
      ('ETH RTL port0 TX—T2',[('U22',47),('U22',46)],[('T2',1),('T2',3)],(0,-1),(0,1),1.05,1.8),
      ('ETH RTL port0 RX—T2',[('U22',44),('U22',45)],[('T2',6),('T2',8)],(0,-1),(0,-1),1.05,1.8),
      ('ETH RTL port1 RX—J7',[('U22',2),('U22',3)],[('J7',1),('J7',2)],(-1,0),(-1,0),1.3,2),
      ('ETH RTL port1 TX—J7',[('U22',5),('U22',4)],[('J7',3),('J7',6)],(-1,0),(1,0),1.3,2),
      ('ETH RTL port2 TX—J18',[('U22',9),('U22',10)],[('J18',3),('J18',6)],(-1,0),(-1,0),1.3,2),
      ('ETH RTL port2 RX—J18',[('U22',12),('U22',11)],[('J18',1),('J18',2)],(-1,0),(1,0),1.3,2),
    ]
    for name,a,b,oa,ob,ea,eb in tasks:
        route_pair(r,name,a,b,oa,ob,ea,eb)
    # Обвязка PHY/средние точки: не трогаем ETH_SH*, это отдельная земля.
    for a,b in [(('T1',2),('C63',1)),(('T1',2),('R50',2)),
                (('T1',7),('C66',1)),(('T1',7),('R51',2)),(('T1',7),('R52',1)),
                (('T1',6),('R51',1)),(('T1',8),('R52',2)),
                (('U10',2),('R48',1)),(('U10',1),('R49',1)),
                (('T2',2),('T2',7)),(('T2',2),('C85',1)),
                (('J7',4),('J7',5)),(('J7',4),('C67',1)),
                (('J18',4),('J18',5)),(('J18',4),('C109',1))]:
        r.connect(a,b,.2,margin=2,step=.1)


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


def fanout(r):
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
        x,y=xy(p.GetPosition());dx,dy=x-cx,y-cy
        sign=1 if (dx if abs(dx)>abs(dy) else dy)>0 else -1
        cp=r.checkpoint();net=p.GetNetname();short=net.split('/')[-1]
        if p.GetNumber()=='41':
            # Один общий VCORE via с pin43: отдельный переход у 41 не
            # помещается между кварцем и IBREF при кольце 0,125 мм.
            path=r.search((x,y),r.pos('U22',43),net,.15,margin=3,step=.05)
            if path and r.track(path,net,.15,label='CORE U22.41—43'):continue
        q=None;stem=None
        # Via требует шага больше 0,4 мм; кроме двух радиусов раздвигаем
        # окончания вдоль ряда. Прямое чередование без веера давало бы
        # clearance .10 мм между via и соседним длинным стволом.
        radii=(1.,1.8,2.6,3.4) if int(p.GetNumber())%2 else (1.8,1.,2.6,3.4)
        north={
            41:((206.4,39.3),[(206.6,41.075),(206.6,39.8),(206.4,39.3)]),
            42:((206.09,40.2),[(206.2,41.075),(206.2,40.8),(206.09,40.2)]),
            43:((205.4,39.3),[(205.8,41.075),(205.8,40.7),(205.4,39.9),(205.4,39.3)]),
        }
        # Переход IBREF близко к своему выводу, CORE расходятся по обе стороны;
        # все три помещаются между рядом .4 мм и трассами кварца без перекрёста.
        if int(p.GetNumber()) in north:
            candidate,path=north[int(p.GetNumber())]
            if r.canvia(candidate,net,.45,.2) and all(r.free(a,b,.15,net) for a,b in zip(path,path[1:])):
                q,stem=candidate,path
        for radius in radii:
            if q is not None:break
            tangents={6:(-.8,),8:(.8,)}.get(int(p.GetNumber()),())+(0,-.4,.4,-.8,.8,-1.2,1.2)
            for tangent in tangents:
                candidate=(x+sign*radius,y+tangent) if abs(dx)>abs(dy) else (x+tangent,y+sign*radius)
                if not r.canvia(candidate,net,.45,.2):continue
                path=r.search((x,y),candidate,net,.15,margin=1,step=.05)
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
        path=r.search(q,dest,net,.2,B,margin=5) if dest else None
        if path is None or not r.track(path,net,.2,B,label='fanout to '+str(key)):
            r.rollback(cp);r.failed.append('fanout B U22.'+p.GetNumber());continue
        backs[key]=dest
    # Все накопительные/развязывающие ёмкости ядра в ту же сеть B.Cu.
    for key in [('C106',1)]+[('C'+str(i),1) for i in range(86,97)]:
        short=r.pad(*key).GetNetname().split('/')[-1]
        master=target[short]
        if key==master:continue
        cp=r.checkpoint();a=back_pad(r,key);b=backs.get(master)
        if b is None:b=back_pad(r,master)
        path=r.search(a,b,r.pad(*key).GetNetname(),.3,B,margin=5) if a and b else None
        if path is None or not r.track(path,r.pad(*key).GetNetname(),.3,B,label='RTL decoupling '+key[0]):
            r.rollback(cp);r.failed.append('RTL decoupling '+key[0]);continue
        backs[master]=b


def main(path):
    board=pcb_route.load(path)
    if any(g.GetName()==TAG for g in board.Groups()):
        raise SystemExit('pcb_preroute: уже выполнено; повторите pcb_build → init на свежей плате')
    if any(t for t in board.GetTracks()):
        raise SystemExit('pcb_preroute: ожидается свежая плата без дорожек')
    expected={'U1':(34,84),'U2':(68,12),'U3':(68,40),'U4':(68,68),
              'U5':(46,26),'U6':(46,56),'U22':(206,44),'Y3':(206,36.5)}
    fp={f.GetReference():f for f in board.GetFootprints()}
    for ref,pos in expected.items():
        if ref not in fp or distance(xy(fp[ref].GetPosition()),pos)>.001:
            raise SystemExit('pcb_preroute: обновите координатные рецепты после смещения '+ref)
    pcbnew.KIID.SeedGenerator(73474)
    r=Router(board)
    thermal(r)
    power(r)
    usb(r)
    clocks(r)
    fanout(r)
    ethernet(r)
    ground(r)
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
