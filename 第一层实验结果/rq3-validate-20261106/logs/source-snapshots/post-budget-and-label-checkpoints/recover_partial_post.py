import argparse,hashlib,json,time,traceback
from pathlib import Path
from native import BASE,Matrix,Layout,chunks
from independent_sorted import metrics
from resource_slots import acquire
ap=argparse.ArgumentParser();ap.add_argument('catalog');args=ap.parse_args();slot=acquire();r=json.loads(Path(args.catalog).read_text());key=Path(args.catalog).stem;old=BASE/'work/post-e'/key;cp=old/'last-completed-sweep.checkpoint.json';out=BASE/'work/stage3-partial-post'/key;out.mkdir(parents=True,exist_ok=True);record=dict(r,status='INCOMPLETE',partial=True,partial_source_checkpoint=str(cp),note='method ended before final P-LS record; last completed sweep independently re-evaluated, no method retry',start=time.time())
try:
 command=json.loads((BASE/'logs'/('stage3-post-'+key+'.command.json')).read_text());assert command.get('ended_at') and command['status']!='RUNNING';actual=json.loads((old/'record.json').read_text()) if (old/'record.json').exists() else {};assert not actual.get('order_path'),'a finished P-LS order exists; do not replace it';d=json.loads(cp.read_text());pi=d['row_perm'];m=Matrix(r['matrix']);assert sorted(pi)==list(range(m.n));tau=int(r['tau']);W=int(r.get('W',16));K=[v for v in pi if m.deg[v]>tau];D=[v for v in pi if m.deg[v]<=tau];checked=metrics(m,chunks(K,W),pi,W);assert checked['sumU']==d['tracked_sumU'] and checked['sumGamma']==d['tracked_sumGamma'];p=out/'order.json';p.write_text(json.dumps(dict(row_perm=pi,partial=True,history=d['history'],status='INCOMPLETE'),separators=(',',':'))+'\n');record.update(order_path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,checkpoint_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),diagnostics=dict(history=d['history'],sweeps_done=len(d['history']),accepted_swaps=sum(s['accepted'] for s in d['history']),tracked_sumU=d['tracked_sumU'],tracked_sumGamma=d['tracked_sumGamma'],independent_full_recompute=checked,incremental_invariant_passed=True),original_command=command);rows=[]
 for diag in [0,1]:
  lc=Layout(m,chunks(K,W),W,diag)
  for dg in [False,True]:
   tm=time.time();row=dict(matrix=m.name,member=r['member'],diag=f'A{diag}',W=W,tau=tau,placement='tail-co',d_rule='D-greedy' if dg else 'own',source='post-E',seed=0,status='INCOMPLETE',post_sec=command.get('actual_method_seconds'),order_sec=r.get('seconds',''),sweeps_done=len(d['history']),accepted_swaps=sum(s['accepted'] for s in d['history']),note='partial P-LS at last completed sweep; original method did not finish; independent U/G exact')
   try:
    sigma,guard=lc.layout(pi,D,'tail-co',dg);a=lc.metrics(sigma);b=metrics(m,chunks(K,W),sigma,W,diag);assert all(a[k]==v for k,v in b.items());row.update(a,**guard)
   except Exception as e:row['note']+='; partial layout evaluation: '+str(e)
   row['d_sec']=time.time()-tm;rows.append(row);(out/'rows.json').write_text(json.dumps(rows,indent=1))
  lc.close()
except Exception as e:record.update(error=str(e),traceback=traceback.format_exc())
record.update(end=time.time());record['seconds']=record['end']-record['start'];(out/'record.json').write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k not in ['diagnostics','traceback','original_command']}),flush=True)
