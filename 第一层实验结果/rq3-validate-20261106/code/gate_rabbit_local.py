import json
from fractions import Fraction
from native import BASE,Matrix
from rabbit_family import coarse_order,local
m=Matrix('cora');adj=m.adjacency();checks=[]
for mode in ['B','U']:
 r=json.loads((BASE/'work/rabbit-coarse'/f'cora-{mode}-repeat0.record.json').read_text());coarse=coarse_order(m,r)
 for W in [16,32]:
  for cn in [False,True]:
   expected=[]
   for start in range(0,len(coarse),8*W):
    rem=coarse[start:start+8*W]
    while rem:
     anchor=rem.pop(0);cur=anchor;expected.append(anchor)
     for k in range(1,W):
      if not rem:break
      ref=cur if cn else anchor;score=lambda v:len(adj[ref]&adj[v]) if cn else Fraction(len(adj[ref]&adj[v]),len(adj[ref]|adj[v]));best=max(range(len(rem)),key=lambda j:score(rem[j]));cur=rem.pop(best);expected.append(cur)
   expected.extend(v for v in range(m.n) if not adj[v]);actual=local(m,coarse,W,cn);assert actual==expected;checks.append(dict(mode=mode,W=W,cn=cn,identical=True))
(BASE/'logs/rabbit-local-gate.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2));print('RABBIT_LOCAL_8_CASES_IDENTICAL')
