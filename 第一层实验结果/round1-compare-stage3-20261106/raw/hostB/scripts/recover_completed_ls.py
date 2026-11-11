import argparse,hashlib,json,time,traceback
from pathlib import Path
from native import BASE,Matrix,chunks
from evaluate_t23 import read_order
from independent_sorted import metrics
from resource_slots import acquire
ap=argparse.ArgumentParser();ap.add_argument('catalog');args=ap.parse_args();slot=acquire();start=time.time()
catalog=Path(args.catalog);r=json.loads(catalog.read_text());key=catalog.stem;old=BASE/'work/post-e'/key;out=BASE/'work/stage3-partial-post'/key;out.mkdir(parents=True,exist_ok=True)
if (out/'record.json').exists():raise SystemExit('derived evidence already exists; leaving it unchanged')
record=dict(r,status='INCOMPLETE',partial=True,partial_scope='original_post_command',incomplete_phase='post_layout_evaluation',start=start,recovery_mode='independent UG check of already completed LS; original saved order reused, no LS or D-stage retry')
try:
 command_path=BASE/'logs'/('stage3-post-'+key+'.command.json');command=json.loads(command_path.read_text())
 assert command.get('ended_at') and command['status']!='RUNNING' and command.get('exitcode') not in [None,0]
 actual=json.loads((old/'record.json').read_text()) if (old/'record.json').exists() else {};assert not actual.get('order_path'),'completed original record exists; do not replace'
 assert not (out/'record.json').exists(),'derived evidence already exists'
 cp=old/'last-completed-sweep.checkpoint.json';d=json.loads(cp.read_text());history=d['history'];assert history and (len(history)==10 or history[-1]['accepted']==0)
 original_order=old/'order.json';saved=json.loads(original_order.read_text());pi=read_order(original_order);assert pi==d['row_perm'];m=Matrix(r['matrix']);assert sorted(pi)==list(range(m.n))
 tau=int(r['tau']);W=int(r.get('W',16));K=[v for v in pi if m.deg[v]>tau];checked=metrics(m,chunks(K,W),pi,W)
 assert checked['sumU']==d['tracked_sumU'] and checked['sumGamma']==d['tracked_sumGamma']
 diag=saved['diagnostics'];assert diag['sweeps_done']==len(history) and diag['incremental_invariant_passed'];assert diag['tracked_sumU']==checked['sumU'] and diag['tracked_sumGamma']==checked['sumGamma']
 source_rows=json.loads((old/'rows.json').read_text()) if (old/'rows.json').exists() else [];rows=[]
 for amode in ['A0','A1']:
  for dr in ['own','D-greedy']:
   row=next((dict(x) for x in source_rows if x['diag']==amode and x['d_rule']==dr),None)
   if row is None:row=dict(matrix=m.name,member=r['member'],W=W,tau=tau,diag=amode,placement='tail-co',d_rule=dr,source='post-E',seed=0,status='INCOMPLETE',post_sec=None,order_sec=r.get('seconds'),note='original post command reached time limit after LS stop condition; column layout unavailable within original budget; no D retry')
   row.update(ls_stop_condition_complete=True,sweeps_done=len(history),accepted_swaps=diag['accepted_swaps']);rows.append(row)
 (out/'rows.json').write_text(json.dumps(rows,indent=1))
 record.update(order_path=str(original_order),sha256=hashlib.sha256(original_order.read_bytes()).hexdigest(),size=original_order.stat().st_size,partial_source_checkpoint=str(cp),checkpoint_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),ls_stop_condition_complete=True,original_command=command,original_command_path=str(command_path),original_completed_condition_count=sum(x['status']=='OK' for x in source_rows),diagnostics=dict(diag,independent_sorted_recompute=checked),note='LS stop condition completed and its original file independently verified; the original post command timed out in column-layout evaluation. Missing conditions remain INCOMPLETE; original successful condition rows are retained exactly.')
except Exception as error:record.update(error=str(error),traceback=traceback.format_exc())
record.update(end=time.time());record['seconds']=record['end']-start;(out/'record.json').write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k not in ['diagnostics','traceback','original_command']}),flush=True)
