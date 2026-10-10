import re,sys
from collections import Counter
t=open(sys.argv[1],encoding='utf-8',errors='replace').read()
m=re.search(r'Begin Object Name="EventGraph"[^\n]*\n(.*?)\n   End Object',t,re.S)
live=set(re.findall(r"Nodes\(\d+\)=\"[^']*'([^']+)'",m.group(1)))
defs=dict(re.findall(r'Begin Object Name="(K2Node_\w+)"[^\n]*\n(.*?)\n\s*End Object',t,re.S))
def sig(b):
    mem=re.search(r'MemberName="([^"]+)"',b)
    pins=[]
    for l in b.splitlines():
        pm=re.search(r'PinName="([^"]+)"',l)
        if pm and pm.group(1) not in ('WorldContextObject','Instigator'): pins.append((pm.group(1), len(re.findall(r'K2Node_\w+ \w{32}',l))))
    return (mem.group(1) if mem else '', tuple(sorted(pins)))
L=Counter(sig(defs[n]) for n in live if n in defs)
g=open(sys.argv[2],encoding='utf-8').read()
G=Counter(sig(b) for n,b in re.findall(r'Begin Object Class=\S+ Name="(K2Node_\w+)"[^\n]*\n(.*?)\nEnd Object',g,re.S))
print('live',sum(L.values()),'gen',sum(G.values()),'diff',list((G-L).keys())[:5],list((L-G).keys())[:5],'msgs',[n for n in live if n in defs and 'bHasCompilerMessage=True' in defs[n]])
