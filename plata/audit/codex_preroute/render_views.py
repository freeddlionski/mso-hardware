"""Векторные слои и обзорные PNG (kicad-cli 9 + PyMuPDF).

python3 render_views.py BOARD.kicad_pcb OUT_DIR
Временный обзор без внешних GND-зон не используется для DRC.
Исходная плата не изменяется. pcbnew/SWIG для удаления зон не нужен.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import fitz

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'kicad/gen'))
from sexp import parse,dump,find

board=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
def pdf(source,layers,target):
    subprocess.run(['kicad-cli','pcb','export','pdf','--mode-single','--layers',layers,'--output',str(target),str(source)],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
for layer in ('F.Cu','In1.Cu','In2.Cu','B.Cu'):
    target=out/(layer+'.pdf');pdf(board,layer+',Edge.Cuts',target)
    doc=fitz.open(target);doc[0].get_pixmap(matrix=fitz.Matrix(2.5,2.5),alpha=False).save(out/(layer+'.png'))
with tempfile.TemporaryDirectory(prefix='mso74-view-') as folder:
    root=Path(folder);view=root/'view.kicad_pcb';tree=parse(board.read_text(encoding='utf-8'))
    def removed(item):
        return isinstance(item,list) and item and item[0]=='zone' and find(item,'layer') in (['layer','F.Cu'],['layer','B.Cu']) and find(item,'net_name')==['net_name','GND'] and not find(item,'locked')
    tree[:]=[item for item in tree if not removed(item)]
    view.write_text(dump(tree)+'\n',encoding='utf-8')
    for ext in ('.kicad_pro','.kicad_dru'):
        if board.with_suffix(ext).exists():shutil.copyfile(board.with_suffix(ext),view.with_suffix(ext))
    for layer in ('F','B'):pdf(view,layer+'.Cu,Edge.Cuts',root/(layer+'.pdf'))
    scale=72/25.4
    for name,layer,bounds in [('power','F',(0,8,88,106)),('signals','F',(170,10,239,81)),('signals-B','B',(170,10,239,81))]:
        doc=fitz.open(root/(layer+'.pdf'));clip=fitz.Rect(*[(x+30)*scale for x in bounds])
        doc[0].get_pixmap(matrix=fitz.Matrix(4,4),clip=clip,alpha=False).save(out/(name+'.png'))
