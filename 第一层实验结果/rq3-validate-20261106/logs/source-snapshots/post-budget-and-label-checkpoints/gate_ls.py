import json
from pathlib import Path
from native import BASE,Matrix
from evaluate_t23 import read_order
from ls_runtime import local_search
reuse=json.loads((BASE/'logs/reused-orders.json').read_text());m=Matrix('cora');base=next(r for r in reuse if r['task']=='T22' and r['use']=='base-order' and r['matrix']=='cora' and r['member']=='C9-Gorder');pi=read_order(base['runtime_path']);checks=[]
for lam in [0,1]:
 order,diag=local_search(m,pi,tau=3,lam=lam);expected=next(r for r in reuse if r['task']=='T22' and r['use']=='M6-reuse' and r['matrix']=='cora' and r['start']=='C9-Gorder' and int(r['tau'])==3 and int(r['lam'])==lam);assert order==read_order(expected['runtime_path']);checks.append(dict(lam=lam,identical_to_T21_sha256=expected['sha256'],diag=diag));print('LS',lam,'IDENTICAL',flush=True)
(BASE/'logs/ls-port-gate.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2))
