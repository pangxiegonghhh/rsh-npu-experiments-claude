import argparse,json,time,hashlib,traceback,resource
from pathlib import Path
from native import BASE,Matrix,Layout,chunks
from evaluate_t23 import read_order
from ls_runtime import local_search
from naming import t23_name
ap=argparse.ArgumentParser();ap.add_argument('record');args=ap.parse_args();r=json.loads(Path(args.record).read_text());out=BASE/'work/post-e'/Path(args.record).stem;out.mkdir(parents=True,exist_ok=True);start=time.time();record=dict(r,status='INCOMPLETE',start=start);rows=[]
r['member']=t23_name(r['member']);record['member']=r['member']
if r['member'] in ['rabbit-pilot','neutron-pilot','B-RCM-ref']:
 record.update(status='SKIPPED',note='historical/reference order; post-E not required by T23 P0 scope',end=time.time());(out/'record.json').write_text(json.dumps(record,indent=2));raise SystemExit(0)
if r['member']=='B1' and not r.get('reuse'):
 old=next((x for x in json.loads((BASE/'logs/reused-orders.json').read_text()) if x['task']=='T23' and x['use']=='post-E-reuse' and x['matrix']==r['matrix'] and 'start=rsh-α0,' in x['params'] and f'tau={r["tau"]},' in x['params']),None)
 if old:r.update(runtime_path=old['runtime_path'],sha256=old['sha256'],reuse=True,reuse_origin=old);record.update(runtime_path=old['runtime_path'],sha256=old['sha256'],reuse=True,reuse_origin=old)
from resource_slots import acquire
cpu_slot=acquire();start=time.time();record['start']=start
try:
 m=Matrix(r['matrix']);tau=int(r['tau']);W=int(r.get('W',16));pi=read_order(r['runtime_path'])
 if r.get('reuse'):
  order=pi;details=json.loads(Path(r['runtime_path']).read_text());diag={k:details.get(k) for k in ['sweeps_done','accepted_swaps']};postsec=0;record.update(order_path=r['runtime_path'],reused_sha256=r['sha256'])
 else:
  order,diag=local_search(m,pi,W,tau,0,0,checkpoint=out/'last-completed-sweep.checkpoint.json');p=out/'order.json';p.write_text(json.dumps(dict(matrix=r['matrix'],member=r['member'],tau=tau,W=W,row_perm=order,diagnostics=diag),separators=(',',':'))+'\n');record.update(order_path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size);postsec=time.time()-start
 D=[v for v in order if m.deg[v]<=tau];K=[v for v in order if m.deg[v]>tau];meta=next(x for x in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if x['matrix']==m.name);t=next(t for t in meta['taus'] if t['tau']==tau)
 for diagmode in [0,1]:
  lc=Layout(m,chunks(K,W),W,diagmode)
  for d in [False,True]:
   tm=time.time();row=dict(matrix=m.name,member=r['member'],diag=f'A{diagmode}',W=W,tau=tau,tau_rule=t['tau_rule'],resid_frac=len(D)/m.n,placement='tail-co',d_rule='D-greedy' if d else 'own',source='post-E',seed=0,status='OK',post_sec=postsec,order_sec=r.get('seconds',''),sweeps_done=diag.get('sweeps_done'),accepted_swaps=diag.get('accepted_swaps'),note='')
   try:sig,guard=lc.layout(order,D,'tail-co',d);row.update(lc.metrics(sig),**guard)
   except Exception as e:row.update(status='INCOMPLETE',note=str(e))
   row['d_sec']=time.time()-tm;rows.append(row);(out/'rows.json').write_text(json.dumps(rows,indent=1))
  lc.close()
 record.update(status='OK' if all(x['status']=='OK' for x in rows) else 'INCOMPLETE',diagnostics=diag)
except Exception as e:record.update(error=str(e),traceback=traceback.format_exc())
record.update(end=time.time());record['seconds']=record['end']-start;record['peak_mem_mb']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20;(out/'record.json').write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k not in ['diagnostics','traceback']}),flush=True)
