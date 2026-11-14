#!/usr/bin/env python3
"""Read-only inventory of pass5 IC pins; not a datasheet validator."""
import csv,collections,pathlib,sys
root=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path(".")
p=root/"plata/audit/pass5/results/ic_pins.csv"
rows=list(csv.DictReader(p.open(encoding="utf-8-sig")))
byref=collections.defaultdict(list)
for r in rows: byref[r["ref"]].append(r)
print("IC instances",len(byref),"IC pins",len(rows))
for ref in sorted(byref):
 rr=byref[ref]
 nc=[r["pin"]+":"+r["pin_name"] for r in rr if r["net"].startswith("unconnected-")]
 print(ref,rr[0]["value"],rr[0]["footprint"],"pins",len(rr),"unconnected",",".join(nc) or "-")
