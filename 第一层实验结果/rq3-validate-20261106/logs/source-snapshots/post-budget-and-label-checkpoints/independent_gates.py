import ast,json,subprocess,sys,time
from pathlib import Path
from native import BASE,Matrix,Layout,chunks,write_runs
from evaluate_t23 import read_order
reuse=json.loads((BASE/'logs/reused-orders.json').read_text());checks=[];out=BASE/'work/independent';out.mkdir(exist_ok=True)
for name in ['cora','wiki-RfA']:
 m=Matrix(name);tau=3;payload={};expected={}
 for method in ['C9-Gorder','rsh-α0','C10-BP']:
  record=next(r for r in reuse if r['task']=='T22' and r['use']=='base-order' and r['matrix']==name and r['member']==method);pi=read_order(record['runtime_path']);D=[v for v in pi if m.deg[v]<=tau];K=[v for v in pi if m.deg[v]>tau];full=chunks(pi);inpl=[[v for v in w if m.deg[v]>tau] for w in full];inpl=[w for w in inpl if w];stats=[]
  for wins in [full,inpl,chunks(K)]:
   lc=Layout(m,wins);stats.append(lc.metrics(pi));lc.close()
  phases=[]
  for s in range(1,16):
   lc=Layout(m,chunks(pi,16,s));phases.append(lc.metrics(pi)['T']);lc.close()
  key=f'{method}|tau{tau}|order';payload[key]=pi;expected[key]=dict(T_full=stats[0]['T'],T_inplace=stats[1]['T'],T_keep=stats[2]['T'],U_inplace=stats[1]['sumU'],U_keep=stats[2]['sumU'],T_full_phase=round(sum(phases)/15,1))
  lc=Layout(m,chunks(K))
  for rule in ['tail','tail-co','gap']:
   sigma,guard=lc.layout(pi,D,rule);s=lc.metrics(sigma);key=f'{method}-{rule}|tau{tau}|sigma';payload[key]=sigma;expected[key]=dict(U=round(s['sumU']/s['k_windows'],2),T=s['T'],R=round(s['sumR']/s['k_windows'],2),write_runs_aic=s['write_runs_aic'],write_runs_resid=write_runs(sigma,D))
  lc.close()
 p=out/(name+'-layouts.json');p.write_text(json.dumps(payload));mtx=BASE/'inputs/t21/inputs'/(name+'.mtx');cmd=[sys.executable,'-I',str(BASE/'repo/第一层工作区/T17-空白二试算脚本/verify/indep_check_rq3.py'),str(mtx),str(p)];start=time.time();r=subprocess.run(cmd,cwd=out,capture_output=True,text=True);(BASE/'logs'/('independent-'+name+'.stdout')).write_text(r.stdout);(BASE/'logs'/('independent-'+name+'.stderr')).write_text(r.stderr);assert r.returncode==0,r.stderr
 actual={}
 for line in r.stdout.splitlines():
  key,value=line.split(' ',1);actual[key]=ast.literal_eval(value)
 assert actual==expected,(name,[(k,v,expected.get(k)) for k,v in actual.items() if v!=expected.get(k)]);checks.append(dict(matrix=name,order_checks=3,sigma_checks=9,placements=['tail','tail-co','gap'],identical=True,command=cmd,exitcode=r.returncode,seconds=time.time()-start));(out/(name+'-expected.json')).write_text(json.dumps(expected,indent=2));print(name,'INDEPENDENT_IDENTICAL',flush=True)
(BASE/'logs/independent-rq3-gates.json').write_text(json.dumps(dict(passed=True,checks=checks),indent=2))
