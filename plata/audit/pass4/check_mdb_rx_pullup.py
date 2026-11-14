#!/usr/bin/env python3
"""Pass 4: focused consistency check. Run from repository root:
python3 plata/audit/pass4/check_mdb_rx_pullup.py
"""
from pathlib import Path
import re
io = Path("plata/kicad/gen/sheet_io.py").read_text(encoding="utf-8")
pinout = Path("plata/PINOUT.md").read_text(encoding="utf-8")
m = re.search(r"def blocked_input\([^\n]*pullup='([^']+)'", io)
assert m, "blocked_input default pullup not found"
assert re.search(r"blocked_input\([^\n]*'MDB_RX_L', 'MDB_RX', 'MDBRX'\)", io), "MDB RX call changed; inspect manually"
pin = next((line for line in pinout.splitlines() if line.startswith("| 35 |")), None)
assert pin, "GPIO35 row missing"
doc = re.search(r"(\d+[.,]?\d*)\s*кОм", pin)
assert doc, "documented GPIO35 pullup not found"
actual = m.group(1).replace("k", "")
print(f"generator MDB_RX pullup: {actual} kOhm")
print(f"PINOUT.md GPIO35 pullup: {doc.group(1)} kOhm")
if float(actual) != float(doc.group(1).replace(",", ".")):
    print("FAIL: documentation disagrees with generator")
    raise SystemExit(1)
print("PASS")
