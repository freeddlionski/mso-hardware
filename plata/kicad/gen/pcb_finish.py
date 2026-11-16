"""Детерминированная доводка снимка route-state 7883e15 после PR #56.

python3 pcb_finish.py INPUT.kicad_pcb OUTPUT.kicad_pcb
Сохраняет прочую авторазводку; добавления закреплены. Удаляются только
мешающие управляющие ветви U1, незавершённые HUBB_C/TP8 и лишний via.
Правила и проект выходного файла сохраняются pcb_route.save().
"""
import json
from pathlib import Path
import sys
import shutil
import tempfile
from sexp import parse,find,findall,dump
import pcbnew
import pcb_route
import pcb_preroute as p


def main(source,out):
    Path(out).resolve().parent.mkdir(parents=True,exist_ok=True)
    # Удалять загруженные зоны через SWIG небезопасно (KiCad 9.0.2).
    # Меняем только нужные S-expression и ссылки групп, затем загружаем
    # новую BOARD: UUID и геометрия остальных дорожек сохраняются.
    tree=parse(Path(source).read_text(encoding='utf-8'));removed=[]
    zones=[z for z in findall(tree,'zone') if find(z,'name') and find(z,'name')[1] in
           (p.TAG+':U1:VIN',p.TAG+':Q1-U1:VIN-top',p.TAG+':Q1:drain')]
    if len(zones)!=3:raise SystemExit('ожидаются три исходные зоны VIN_B')
    keeper=next(z for z in zones if find(z,'name')[1].endswith('U1:VIN'))
    find(keeper,'name')[1]=p.TAG+':Q1-U1:VIN';find(keeper,'priority')[1]='12'
    find(find(keeper,'polygon'),'pts')[1:]=[['xy',str(x+30),str(y+30)] for x,y in
        ((29.4,76),(49.4,76),(49.4,86.4),(44.1,86.4),(44.1,80.2),(31.9,80.2),(31.9,82.9),(29.4,82.9))]
    # Только незавершённая авто-ветвь TP8, не закреплённое дерево CORE.
    original=pcbnew.LoadBoard(source);temp_router=p.Router(original)
    core=p.SupplyGraph(temp_router,'SW_VCORE',('TP8',1))
    tp8_ids={t.m_Uuid.AsString() for t in original.GetTracks()
             if t.GetNetname()=='SW_VCORE' and not t.IsLocked() and core.linked(t)}
    del core,temp_router,original
    deleted=set()
    for z in zones:
        if z is keeper:continue
        uid=find(z,'uuid')[1];deleted.add(uid);removed.append({'uuid':uid,'kind':'zone','name':find(z,'name')[1]});tree.remove(z)
    # Четыре управляющие сети U1 мешают силовой перемычке/выходу U1;
    # незавершённая HUBB_C перестраивается отдельно.
    # Остальная Freerouting-медь остаётся с исходными UUID и геометрией.
    reroute={'/Питание/EF_DRV','/Питание/EF_BGATE','/Питание/EF_PGTH','/Питание/EF_SHDN','/Табло и часы/HUBB_C'}
    nets={n[1]:n[2] for n in findall(tree,'net')}
    for kind in ('segment','via'):
        for item in list(findall(tree,kind)):
            ni=find(item,'net');uid=find(item,'uuid')[1]
            if (ni and nets.get(ni[1]) in reroute) or uid in tp8_ids:
                if find(item,'locked') or 'locked' in item:raise RuntimeError('защищённая медь '+nets[ni[1]])
                reason=('TP8: выход вне опорных коридоров Ethernet' if uid in tp8_ids else
                        'HUBB_C: обход препятствий' if nets[ni[1]].endswith('/HUBB_C') else
                        'U1: выход управления и восстановление VIN_B')
                deleted.add(uid);removed.append({'uuid':uid,'kind':kind,'net':nets[ni[1]],'reason':reason});tree.remove(item)
    redundant={'922d4be2-d0f3-4322-a4dc-016198679f24','bbcc40dc-56b9-4602-b3d5-f2d6b6841f85'}
    for v in list(findall(tree,'via')):
        uid=find(v,'uuid')[1]
        if uid in redundant:
            deleted.add(uid);removed.append({'uuid':uid,'kind':'via','at_mm':[float(n)-30 for n in find(v,'at')[1:3]]});tree.remove(v)
    # IN_SYS — только измерительный/служебный ток. Уменьшение одного
    # via 0,60/0,30 → 0,45/0,20 освобождает два выхода управления U1.
    for via in findall(tree,'via'):
        if find(via,'uuid')[1]=='bb2a6ca2-1fe2-47c4-896d-4805b344bf7d':
            find(via,'size')[1]='0.45';find(via,'drill')[1]='0.2'
    for group in findall(tree,'group'):
        members=find(group,'members')
        if members:members[1:]=[uid for uid in members[1:] if uid not in deleted]
    for z in findall(tree,'zone'):
        z[:]=[item for item in z if not (isinstance(item,list) and item and item[0]=='filled_polygon')]
    # Загрузка временного входа с теми же настройками, результат отдельно.
    with tempfile.TemporaryDirectory(prefix='mso74-finish-',dir=Path(out).resolve().parent) as tmp:
        prepared=Path(tmp)/'input.kicad_pcb';prepared.write_text(dump(tree)+'\n',encoding='utf-8')
        pro=Path(source).with_suffix('.kicad_pro')
        if pro.exists():shutil.copyfile(pro,prepared.with_suffix('.kicad_pro'))
        b=pcb_route.load(str(prepared))
        pcbnew.KIID.SeedGenerator(741604)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    r=p.Router(b,protect_zones=True);r.group.SetName('MSO74_ROUTE_FINAL_V1')
    p.pmic_details(r)
    p.power_details(r)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcb_route.save(b,out)
    manifest={'source_state':'7883e15','removed':removed,'routes':r.done,'not_routed':r.failed,
              'added':[{'uuid':t.m_Uuid.AsString(),'kind':'via' if isinstance(t,pcbnew.PCB_VIA) else 'track'} for t in r.created]}
    Path(out).with_suffix('.finish.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('finish: добавлено %d объектов; неполных рецептов %d'%(len(r.created),len(r.failed)),flush=True)
    if r.failed:raise SystemExit(1)


if __name__=='__main__':main(*sys.argv[1:])
