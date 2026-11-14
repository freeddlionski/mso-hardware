#!/usr/bin/env python3
"""Overlay KiCad SMD rectangles on a TI PDF drawing, with explicit manual calibration.
Requires PyMuPDF and Pillow. Never use page display scale as physical scale.
Example:
 python pass8_overlay.py --pdf lm61460.pdf --page 55 --footprint LM.kicad_mod --x1 100 --x2 300 --mm1 -2 --mm2 2 --cx 200 --cy 400 --output pass8_lm61460.png
All PDF coordinates in points; page index is zero-based. x1/x2 must be two ends of a dimension on the drawing, mm1/mm2 their real values. cx/cy are the physical footprint origin in PDF points.
"""
import argparse,re,fitz
from PIL import Image,ImageDraw
p=argparse.ArgumentParser()
for n in ('pdf','footprint','output'):p.add_argument('--'+n,required=True)
for n in ('x1','x2','mm1','mm2','cx','cy'):p.add_argument('--'+n,type=float,required=True)
p.add_argument('--page',type=int,required=True)
p.add_argument('--dpi',type=int,default=300)
a=p.parse_args()
s=open(a.footprint,encoding='utf8').read()
pat=r'\(pad\s+"([^"]*)"\s+smd\s+rect\s+\(at\s+([-\d.]+)\s+([-\d.]+)\)\s+\(size\s+([-\d.]+)\s+([-\d.]+)\)'
pads=[(n,*map(float,(x,y,w,h))) for n,x,y,w,h in re.findall(pat,s)]
pg=fitz.open(a.pdf)[a.page]; z=a.dpi/72
pix=pg.get_pixmap(matrix=fitz.Matrix(z,z),alpha=False)
im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples).convert('RGBA')
d=ImageDraw.Draw(im,'RGBA')
scale=(a.x2-a.x1)/(a.mm2-a.mm1)*z
for n,x,y,w,h in pads:
 px=a.cx*z+x*scale;py=a.cy*z+y*scale
 d.rectangle((px-w*scale/2,py-h*scale/2,px+w*scale/2,py+h*scale/2),fill=(255,0,0,75),outline=(255,0,0,255),width=2)
im.convert('RGB').save(a.output)
print('Calibration requires independent confirmation against another printed dimension.')
