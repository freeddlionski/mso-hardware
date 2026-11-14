#!/usr/bin/env python3
"""Run: python3 plata/audit/pass5/gpio_check.py ../mso74-plata.xml"""
import sys,xml.etree.ElementTree as ET
r=ET.parse(sys.argv[1]).getroot()
pins={x.get('pinfunction'):n.get('name') for n in r.findall('./nets/net') for x in n.findall('node') if x.get('ref')=='U7'}
expected={1:'HUB_LAT',2:'HUB_OE',3:'HUB_CLK',4:'HUB_C',5:'HUB_A',6:'HUB_B2',7:'VTK_TX',8:'BILL_PULSE',9:'COIN_PULSE',10:'ETH_CS',11:'ETH_MOSI',12:'ETH_SCLK',13:'ETH_MISO',14:'ETH_INT',15:'VTK_RX',16:'HUB_R2',17:'HUB_B1',18:'HUB_R1',19:'HUB_D',20:'SERVICE_BTN',21:'HUB_B',35:'MDB_RX',36:'COIN_INH',37:'MDB_TX',38:'RS485_DE',39:'RS485_TX',40:'RS485_RX',41:'HUB_G2',42:'HUB_G1',43:'U0_TX',44:'U0_RX',47:'RTC_SCL',48:'RTC_SDA'}
fail=0
for n,want in sorted(expected.items()):
 symbol={19:'USB_D-',20:'USB_D+',43:'TXD0',44:'RXD0'}.get(n,f'IO{n}')
 actual=pins.get(symbol,'MISSING').split('/')[-1]
 ok=actual==want;fail+=not ok
 print('PASS' if ok else 'FAIL','GPIO',n,'expected',want,'actual',actual)
for n in (45,46):print('NC',n,pins.get(f'IO{n}'))
print('mismatches',fail)
raise SystemExit(bool(fail))
