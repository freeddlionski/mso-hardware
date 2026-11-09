"""Сводный DXF на резку модуля табло: все детали с количеством, подписи на слое LABEL."""
import os, sys
D = sys.argv[1]; OUT = sys.argv[2]
P = [("T1_lico", 1, "T1 Лицо", 0), ("T3_obechayka_P", 1, "T3 П-обечайка", 2+1), ("T4_dno_koryto", 1, "T4 Дно-корыто", 3),
     ("T6_kryshka", 1, "T6 Крышка", 4), ("T2_skoba_matricy", 2, "T2 Z-скоба", 2), ("T5_ugolok_din", 2, "T5 Уголок DIN", 1)]

def ents(path):
    raw = open(path, encoding="cp1251").read().replace("\r\n", "\n").split("\n")
    i = raw.index("ENTITIES") + 1; end = len(raw) - 1 - raw[::-1].index("ENDSEC")
    pairs = [(raw[k].strip(), raw[k + 1]) for k in range(i, end - 1, 2)]
    out, cur = [], []
    for c, v in pairs:
        if c == "0" and cur: out.append(cur); cur = []
        cur.append((c, v))
    if cur: out.append(cur)
    return out

def bbox(es):
    xs, ys = [], []
    for e in es:
        d = dict((c, v) for c, v in e if c in ("10", "20", "11", "21", "40"))
        typ = e[0][1]
        if typ in ("LINE",):
            xs += [float(d["10"]), float(d["11"])]; ys += [float(d["20"]), float(d["21"])]
        elif typ in ("ARC", "CIRCLE"):
            r = float(d["40"]); xs += [float(d["10"]) - r, float(d["10"]) + r]; ys += [float(d["20"]) - r, float(d["20"]) + r]
    return min(xs), min(ys), max(xs), max(ys)

GAP, ROWW = 25, 1200
x = y = 0; rowh = 0; body = []; summary = []
for key, qty, name, bends in P:
    es = ents(os.path.join(D, key + ".dxf"))
    cut = [e for e in es if dict(e).get("8") == "CUT"]
    x0, y0, x1, y1 = bbox(cut); w, h = x1 - x0, y1 - y0
    summary.append((name, qty, w, h, bends))
    for n in range(qty):
        if x + w > ROWW: x = 0; y += rowh + GAP + 15; rowh = 0
        for e in es:
            s = []
            for c, v in e:
                if c in ("10", "11"): v = f"{float(v) - x0 + x:.3f}"
                if c in ("20", "21"): v = f"{float(v) - y0 + y:.3f}"
                s += [c, v]
            body.append("\n".join(s))
        body.append(f"0\nTEXT\n8\nLABEL\n10\n{x:.3f}\n20\n{y + h + 4:.3f}\n30\n0\n40\n6\n1\n{name.split()[0]}" + (f" {n + 1}/{qty}" if qty > 1 else ""))
        x += w + GAP; rowh = max(rowh, h)
legend = "Модуль табло МСО74 — нерж. AISI 304, 1,5 мм. Слой CUT — резать, MARK — линии гиба (не резать), ENGRAVE — гравировка/маркировка. " + "; ".join(f"{n} - {q} шт." for n, q, *_ in summary)
body.append(f"0\nTEXT\n8\nLABEL\n10\n0\n20\n{y + rowh + 40:.3f}\n30\n0\n40\n7\n1\n{legend}")
head = ("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n9\n$DWGCODEPAGE\n3\nANSI_1251\n9\n$INSUNITS\n70\n4\n0\nENDSEC\n"
        "0\nSECTION\n2\nTABLES\n0\nTABLE\n2\nLAYER\n70\n4\n"
        "0\nLAYER\n2\nCUT\n70\n0\n62\n7\n6\nCONTINUOUS\n"
        "0\nLAYER\n2\nMARK\n70\n0\n62\n1\n6\nCONTINUOUS\n"
        "0\nLAYER\n2\nENGRAVE\n70\n0\n62\n5\n6\nCONTINUOUS\n"
        "0\nLAYER\n2\nLABEL\n70\n0\n62\n3\n6\nCONTINUOUS\n0\nENDTAB\n0\nENDSEC\n")
open(OUT, "w", encoding="cp1251", newline="\r\n").write(head + "0\nSECTION\n2\nENTITIES\n" + "\n".join(body) + "\n0\nENDSEC\n0\nEOF\n")
for r in summary: print("%-16s x%d  %7.2f x %7.2f  гибов %d" % r)
