import argparse,json,time,traceback
from pathlib import Path
from native import BASE,Matrix,Layout,Candidates,chunks
from evaluate_t23 import read_order
from naming import t23_name
from resource_slots import acquire
cpu_slot=acquire()
ap=argparse.ArgumentParser();ap.add_argument('record');args=ap.parse_args();r=json.loads(Path(args.record).read_text());out=BASE/'work/t23-diagnostics'/Path(args.record).stem;out.mkdir(parents=True,exist_ok=True);start=time.time();status=dict(status='INCOMPLETE')
try:
 m=Matrix(r['matrix']);pi=read_order(r['runtime_path']);member=t23_name(r.get('t23_member',r.get('method')));meta=next(x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if x['matrix']==m.name);tau=meta['taus'][-1]['tau'];offsets=list(range(1,16));phases=[]
 for s in offsets:
  lc=Layout(m,chunks(pi,16,s));phases.append(dict(offset=s,**lc.metrics(pi)));lc.close()
 lc=Layout(m,chunks(pi));full=lc.metrics(pi);lc.close();inplace=[[v for v in w if m.deg[v]>tau] for w in chunks(pi)];inplace=[w for w in inplace if w];K=[v for v in pi if m.deg[v]>tau];metrics=[]
 for wins in [inplace,chunks(K)]:
  lc=Layout(m,wins);metrics.append(lc.metrics(pi));lc.close()
 diag=dict(matrix=m.name,member=member,W=16,diag='A0',tau=tau,T_full=full['T'],T_full_phase=sum(x['T'] for x in phases)/15,align_premium=sum(x['T'] for x in phases)/15-full['T'],T_inplace=metrics[0]['T'],T_keep=metrics[1]['T'],U_inplace=metrics[0]['sumU'],U_keep=metrics[1]['sumU'],offsets_used=offsets,diagnostic_seconds=time.time()-start,status='OK')
 extras=r.get('diagnostics',{});groups=[]
 if member in ['C2-LSH','C3-W1','C3-W4']:
  graph=Candidates(m);actual,extras=graph.order(member);graph.close();assert actual==pi,'diagnostic reconstruction changed order';sizes=extras['evaluation_group_sizes'];pos=0;wins=[]
  for size in sizes:wins.append(pi[pos:pos+size]);pos+=size
  wins+=chunks(pi[pos:]);lc=Layout(m,wins);own=lc.metrics(pi);lc.close()
  for boundary,s in [('candidate groups',own),('W16 evaluation windows',full)]:groups.append(dict(matrix=m.name,member=member,W=16,boundary=boundary,k_windows=s['k_windows'],sumU=s['sumU'],T=s['T'],diagnostic_only=True))
  diag.update({k:extras[k] for k in ['groups_full_before','short_before','P_merges','P_new_full','short_after','groups_cut_by_windows']})
 if member.startswith('C1-'):diag.update({k:extras.get(k) for k in ['graph_components','graph_edges','zero_distance_edges','recall_at16']})
 (out/'diag.json').write_text(json.dumps(diag,indent=2));(out/'groups.json').write_text(json.dumps(groups,indent=2));(out/'phases.json').write_text(json.dumps(phases,indent=1));(out/'candidate-diagnostics.json').write_text(json.dumps(extras,indent=2));status=dict(status='OK',seconds=time.time()-start)
except Exception as e:status=dict(status='INCOMPLETE',error=str(e),traceback=traceback.format_exc(),seconds=time.time()-start)
(out/'status.json').write_text(json.dumps(status,indent=2));print(json.dumps(status),flush=True)
