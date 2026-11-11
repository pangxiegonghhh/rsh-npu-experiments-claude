import csv,json
from native import BASE,Matrix,Layout,chunks
from evaluate_t23 import read_order
from resource_slots import acquire
token=acquire();reuse=json.loads((BASE/'logs/reused-orders.json').read_text());joint=list(csv.DictReader(open(BASE/'inputs/t21/joint.csv')));checks=[];matrices={}
for r in reuse:
 if r['task']!='T22' or r['use']!='M6-reuse':continue
 m=matrices.setdefault(r['matrix'],Matrix(r['matrix']));pi=read_order(r['runtime_path']);tau=int(r['tau']);kept=[v for v in pi if m.deg[v]>tau];lc=Layout(m,chunks(kept));stats=lc.metrics(pi);lc.close();old=next(x for x in joint if x['matrix']==r['matrix'] and x['member']=='P-LS' and x['start']==r['start'] and int(x['tau'])==tau and float(x['lambda'])==float(r['lam']) and x['seed']=='0' and x['diag']=='A0' and x['d_rule']=='own' and x['placement']=='tail');assert stats['sumU']==int(old['sumU']) and stats['sumGamma']==int(old['sumGamma']),r;data=json.loads(open(r['runtime_path']).read());checks.append(dict(matrix=r['matrix'],member=r['start'],tau=tau,lam=float(r['lam']),seed=0,sumU=stats['sumU'],sumGamma=stats['sumGamma'],T=stats['T'],sweeps_done=data['sweeps_done'],accepted_swaps=data['accepted_swaps'],T21_order_sec=float(old['order_sec']),source_path=r['runtime_path'],source_sha256=r['sha256'],identical_to_T21_joint=True));print(r['matrix'],r['start'],tau,r['lam'],'U/G_IDENTICAL',flush=True)
(BASE/'logs/reused-pls-invariants.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2))
