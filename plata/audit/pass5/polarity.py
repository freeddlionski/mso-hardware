#!/usr/bin/env python3
"""Run: python3 plata/audit/pass5/polarity.py ../mso74-plata.xml"""
import pathlib,sys,xml.etree.ElementTree as ET
r=ET.parse(sys.argv[1]).getroot()
cs={c.get('ref'):c for c in r.findall('./components/comp')}
pins={(x.get('ref'),x.get('pin')):n.get('name') for n in r.findall('./nets/net') for x in n.findall('node')}
for ref,c in sorted(cs.items()):
 if not ref.startswith('D'):continue
 v=c.findtext('value') or ''
 a,b=pins.get((ref,'1')),pins.get((ref,'2'))
 if v.startswith(('SMAJ','SMCJ')):
  status='BIDIRECTIONAL' if v.endswith('CA') else ('PASS pad1 cathode' if b=='GND' and a!='GND' else 'REVIEW')
 elif v.startswith(('BAT46','BAT54','1N4148','SS34')):status='CHECK physical pad mapping; netlist only'
 else:continue
 print(ref,v,'pad1',a,'pad2',b,status)
