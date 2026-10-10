"""Static checks on generated paste text: every link two-sided, no exec input left dangling, no pure node whose
outputs go nowhere, and every self variable the graph uses is declared in setup_assets.py.
Usage: python check_paste.py <paste.txt> [setup_assets.py]
"""
import re
import sys

t = open(sys.argv[1], encoding="utf-8").read()
blocks = re.findall(r'Begin Object Class=(\S+) Name="([^"]+)"(.*?)\nEnd Object', t, re.S)
pins, bad = {}, 0
for klass, name, body in blocks:
    for line in body.splitlines():
        m = re.search(r'PinId=(\w+),PinName="([^"]+)"', line)
        if m:
            links = re.findall(r'(\w+) (\w{32}),', line.split("LinkedTo=(")[1].split(")")[0]) if "LinkedTo=(" in line else []
            pins[(name, m.group(1))] = (m.group(2), links, line)
for (n, pid), (pname, links, _) in pins.items():
    for ln, lp in links:
        if (ln, lp) not in pins or (n, pid) not in pins[(ln, lp)][1]:
            bad += 1
            print("one-sided link:", n, pname, "->", ln)
for klass, name, body in blocks:
    comment = re.search(r'NodeComment="([^"]*)"', body)
    for pn in ("execute", "Exec"):
        m = re.search(r'PinName="%s",[^\n]*' % pn, body)
        if m and "LinkedTo" not in m.group(0) and "K2Node_Event" not in klass:
            bad += 1
            print("dead exec:", name, comment.group(1) if comment else "")
    if "bIsPureFunc" in body or "VariableGet" in klass:
        outs = [l for l in body.splitlines() if "EGPD_Output" in l]
        if outs and not any("LinkedTo" in l for l in outs):
            bad += 1
            print("unused pure:", name)
used = set(re.findall(r'VariableReference=\(MemberName="(\w+)",bSelfContext=True\)', t))
if len(sys.argv) > 2:
    declared = set(re.findall(r'\("(\w+)", ', open(sys.argv[2], encoding="utf-8").read()))
    for v in sorted(used - declared):
        bad += 1
        print("variable not declared in setup:", v)
print(f"{len(blocks)} objects, {len(pins)} pins, {len(used)} self variables, problems: {bad}")
sys.exit(1 if bad else 0)
