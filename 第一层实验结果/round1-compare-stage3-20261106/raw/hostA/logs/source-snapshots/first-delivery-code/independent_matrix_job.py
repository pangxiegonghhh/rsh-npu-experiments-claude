import argparse,ast,csv,json,subprocess,sys,time,traceback
from pathlib import Path
from resource_slots import acquire
from native import BASE,Matrix,Layout,chunks
from evaluate_t23 import read_order
ap=argparse.ArgumentParser();ap.add_argument('matrix');args=ap.parse_args();token=acquire();start=time.time();out=BASE/'work/independent-all'/args.matrix;out.mkdir(parents=True,exist_ok=True);result=dict(matrix=args.matrix,status='INCOMPLETE',start=start)
try:
 m=Matrix(args.matrix);reuse=json.loads((BASE/'logs/reused-orders.json').read_text());meta=next(x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if x['matrix']==m.name);tau=meta['taus'][-1]['tau'];fullpayload={};rq3payload={};expectfull={};expectrq3={};consistency=[];t21=list(csv.DictReader(open(BASE/'inputs/t21/results.csv')))
 for member in ['B0','C9-Gorder','C10-BP']:
  r=next(r for r in reuse if r['task']=='T22' and r['use']=='base-order' and r['matrix']==m.name and r['member']==member);pi=read_order(r['runtime_path']);lc=Layout(m,chunks(pi));fm=lc.metrics(pi);lc.close();fullpayload[member]=pi;expectfull[member]=(round(fm['sumU']/fm['k_windows'],2),fm['T'],round(fm['sumGamma']/fm['k_windows'],2),round(fm['sumR']/fm['k_windows'],2));old=next(x for x in t21 if x['matrix']==m.name and x['member']==member and x['W']=='16' and x['tau']=='none' and x['diag']=='A0' and x['d_rule']=='own');assert int(old['sumU'])==fm['sumU'] and int(old['T'])==fm['T'];consistency.append(dict(member=member,sumU=fm['sumU'],T=fm['T'],T21_identical=True))
  K=[v for v in pi if m.deg[v]>tau];wins=[[v for v in w if m.deg[v]>tau] for w in chunks(pi)];wins=[w for w in wins if w];metrics=[]
  for ws in [wins,chunks(K)]:
   lc=Layout(m,ws);metrics.append(lc.metrics(pi));lc.close()
  phases=[]
  for s in range(1,16):
   lc=Layout(m,chunks(pi,16,s));phases.append(lc.metrics(pi)['T']);lc.close()
  key=f'{member}|tau{tau}|order';rq3payload[key]=pi;expectrq3[key]=dict(T_full=fm['T'],T_inplace=metrics[0]['T'],T_keep=metrics[1]['T'],U_inplace=metrics[0]['sumU'],U_keep=metrics[1]['sumU'],T_full_phase=round(sum(phases)/15,1))
 def check(script,payload,expected,label):
  p=out/(label+'-input.json');p.write_text(json.dumps(payload));cmd=[sys.executable,'-I',str(script),meta['input_path'],str(p)];tm=time.time();r=subprocess.run(cmd,cwd=out,capture_output=True,text=True,timeout=7200);(out/(label+'.stdout')).write_text(r.stdout);(out/(label+'.stderr')).write_text(r.stderr);assert r.returncode==0,r.stderr;actual={k:ast.literal_eval(v) for k,v in (line.split(' ',1) for line in r.stdout.splitlines())};assert actual==expected,(actual,expected);return dict(script=str(script),command=cmd,exitcode=0,seconds=time.time()-tm,orders=3,identical=True)
 checks=[check(BASE/'repo/第一层工作区/T17-空白一试算脚本/verify/indep_check.py',fullpayload,expectfull,'rq2-independent'),check(BASE/'repo/第一层工作区/T17-空白二试算脚本/verify/indep_check_rq3.py',rq3payload,expectrq3,'rq3-independent')];result.update(status='OK',checks=checks,T21_consistency=consistency,expected_full=expectfull,expected_four=expectrq3)
except Exception as e:result.update(error=str(e),traceback=traceback.format_exc())
result.update(end=time.time());result['seconds']=result['end']-start;(out/'status.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
