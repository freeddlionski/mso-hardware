#!/usr/bin/env python3
"""Run: python3 plata/audit/pass5/calculate.py. Illustrative DC calculations, not SPICE."""
import itertools
a,b,c=390000,19100,15000
for name,fn in [('UVLO',lambda a,b,c:(a+b+c)/(b+c)),('OVP',lambda a,b,c:(a+b+c)/c)]:
 vals=[1.2*v*fn(x,y,z) for v,x,y,z in itertools.product((.98,1.02),(a*.99,a*1.01),(b*.99,b*1.01),(c*.99,c*1.01))]
 print(name,'nominal',round(1.2*fn(a,b,c),3),'min',round(min(vals),3),'max',round(max(vals),3),'V')
for vf in (.2,.35,.5):
 i=(3.3-vf)/10330
 print('blocked_input Vf',vf,'I_mA',round(i*1000,4),'GPIO_V',round(vf+330*i,4))
print('blocked_input +32V: BAT46 reverse-biased; leakage unknown without vendor/temperature specification')
for v in (4.5,5.5):
 i=(v-.4-1.2)/370
 print('MDB VCC',v,'total_mA',round(i*1000,3),'each_mA',round(i*500,3),'pin5_V',round(1.2+220*i,3))
i=(3.94-.4-1.2)/370
print('MDB VOH assumed 3.94V: total_mA',round(i*1000,3),'pin5_V',round(1.2+220*i,3))
