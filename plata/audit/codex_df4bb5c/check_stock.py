#!/usr/bin/env python3
"""Read-only public catalog snapshot. Numbers are NOT procurement reservations.
Portable version of the collection logic used for the audit; uses only Python's standard library.
Usage: python3 check_stock.py --bom /path/to/bom.csv --out /tmp/new-stock
Do not overwrite the historical audit snapshot when checking a later date.
"""
import argparse,csv,datetime,json,re,time,urllib.request,urllib.error
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--bom',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
parts={}
for row in csv.DictReader(args.bom.open()):parts.setdefault(row['LCSC'],[]).append(row['Reference'])
headers={'User-Agent':'Mozilla/5.0'}
def request(url,data=None):
    h=dict(headers)
    if data is not None:h['Content-Type']='application/json'
    return urllib.request.urlopen(urllib.request.Request(url,data=data,headers=h),timeout=30).read().decode()
def next_chunks(s):
    chunks=[]
    for m in re.finditer(r'self.__next_f.push\((\[.*?\])\)</script>',s):
        try:
            j=json.loads(m[1])
            if len(j)>1 and isinstance(j[1],str):chunks.append(j[1])
        except ValueError:pass
    return ''.join(chunks)
def lcsc(code):
    url='https://www.lcsc.com/product-detail/'+code+'.html';stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        s=request(url);d,_=json.JSONDecoder().raw_decode(s[s.index('"webData":')+10:])
        if not isinstance(d,dict):raise ValueError('empty product object')
        out={k:d.get(k)for k in ['productCode','productModel','brandNameEn','encapStandard','stockNumber','productCycle','isForeignOnsale','pdfUrl','paramVOList']}
    except Exception as e:out={'error':str(e)}
    return dict(out,url=url,fetched_utc=stamp,refs=parts[code])
def jlc(code):
    url='https://jlcpcb.com/partdetail/part/'+code;stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        s=next_chunks(request(url));out=None
        for m in re.finditer(r'^\w+:\{',s,re.M):
            try:d,_=json.JSONDecoder().raw_decode(s[m.end()-1:])
            except ValueError:continue
            if d.get('componentCode')==code and 'componentLibraryType'in d:
                out={k:d.get(k)for k in ['componentCode','componentModelEn','componentBrandEn','componentSpecificationEn','componentLibraryType','overseasStockCount','canPresaleNumber','isBuyComponent','noBuyReason','dataManualUrl','replaceUrlSuffix','componentAlternativesCode']};break
        if out is None:raise ValueError('main product object not found')
    except Exception as e:out={'error':str(e)}
    return dict(out,url=url,fetched_utc=stamp)
ls={};js={}
for code in parts:
    ls[code]=lcsc(code);time.sleep(.8);js[code]=jlc(code);time.sleep(1.2)
    # Preserve completed work even if a later request fails or the service rate-limits.
    (args.out/'lcsc_snapshot.json').write_text(json.dumps(ls,ensure_ascii=False,indent=2));(args.out/'jlc_snapshot.json').write_text(json.dumps(js,ensure_ascii=False,indent=2))
    print(code,'L=',ls[code].get('stockNumber'),'J=',js[code].get('overseasStockCount'),js[code].get('error',''),flush=True)
    if any('429'in v.get('error','')for v in [ls[code],js[code]]):
        print('Rate limited; snapshot preserved. Wait before resuming requests.');break
