import concurrent.futures,hashlib,json,os,sys,time
from pathlib import Path
from native import BASE
from bounded_case import run_case
from stage3_catalog import catalog,P1
from collect_t23_first import P0

def environment(kind):
 e=os.environ.copy();e.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',NUMBA_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
 if kind=='external':e['PYTHONPATH']=str(BASE/'deps/python')+os.pathsep+str(BASE/'scripts')
 if kind=='hp':e['PYTHONPATH']=str(BASE/'deps/kahypar-runtime')+os.pathsep+str(BASE/'scripts')
 return e
def generator(r):
 m,c,W,s=r['matrix'],r['method'],r['W'],r['seed'];key=f'{m}__{c}__W{W}__seed{s}';common=['--matrix',m,'--W',str(W)]
 if c in ['C1-J','C1-H']:script='external_c1.py';args=['--matrix',m,'--variant',c[-1],'--seed',str(s)];folder='external';env='external'
 elif c=='C8-METIS':script='external_metis.py';args=common;folder='external';env='external'
 elif c=='C6-HP':script='external_hp.py';args=common;folder='stage3-generated';env='hp'
 elif c.startswith('C5'):script='rabbit_family.py';args=common+['--mode','U' if c.startswith('C5-U') else 'B','--rep',str(s)]+(['--cn'] if c.endswith('-CN') else []);folder='external';env='main'
 elif c in P1:script='stage3_p1.py';args=common+['--method',c,'--seed',str(s)];folder='stage3-generated';env='main'
 elif c in ['C2-LSH','C3-W1','C3-W4','C4-U','C4-T','C7-I']:script='generate_pure.py';args=common+['--method',c,'--seed',str(s)];folder='generated';env='main'
 else:script='new_full_order.py';args=common+['--method',c,'--seed',str(s)];folder='stage3-generated';env='main'
 return [sys.executable,'-B','scripts/'+script]+args,BASE/'work'/folder/(key+'.record.json'),environment(env)
def run(r):
 case=r['case_id'];folder=BASE/'work/stage3-cases'/case;folder.mkdir(parents=True,exist_ok=True);result=folder/'record.json'
 if result.exists():return json.loads(result.read_text())
 begin=time.time();record=dict(r,status='INCOMPLETE',start=begin)
 if r.get('data_missing'):record.update(status='SKIPPED',error='official TAMU403; files-server TLS timeout; UF official fallback404; see secondbatch input logs')
 elif r['matrix'] in ['reddit','ogbn-products'] and r['method'].startswith('C6-') and r['method']!='C6-HP':record.update(status='SKIPPED',error='dispatch requires frozen T21 C6-RB/M orders, unavailable for second-batch matrices; no rerun under T21 label')
 elif r['method']=='C6-HP' and not json.loads((BASE/'logs/hp-repeated-cora-gate.json').read_text())['passed']:record.update(status='INCOMPLETE',error='HP Cora same-seed gate did not pass; no unverified HP order reported')
 else:
  if r.get('reuse'):
   old=r['reuse'];p=Path(old.get('runtime_path',old.get('path','')));assert p.exists();h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==old['sha256'];record.update(runtime_path=str(p),path=str(p),sha256=h,size=p.stat().st_size,seconds=old.get('seconds',''),diagnostics=old.get('diagnostics',{}),status='OK',reused=True)
  else:
   cmd,p,env=generator(r)
   if not p.exists():
    command=run_case(cmd,'stage3-order-'+case,env=env);record['generation_command']=command
   if p.exists():
    actual=json.loads(p.read_text());record.update(actual);record.update(method=r['method'],member=r['method'],W=r['W'],seed=r['seed'],case_id=case,scope=r['scope']);record['runtime_path']=actual.get('runtime_path',actual.get('path'))
   else:record.update(error='generator exited/terminated before a final order record; see generation_command',status='INCOMPLETE')
  if record['status']=='OK':
   record.update(evaluation_root='stage3-evaluations',diagnostic_root='stage3-diagnostics')
   if r.get('main_tau_only'):
    meta=next(m for m in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if m['matrix']==r['matrix']);record['eval_taus']=[meta['taus'][-1]['tau']]
   p=BASE/'work/stage3-eval-catalog'/(case+'.json');p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(record,ensure_ascii=False,indent=2));ev=BASE/'work/stage3-evaluations'/case/'status.json'
   if not ev.exists():run_case([sys.executable,'-B','scripts/evaluate_t23.py',str(p)],'stage3-eval-'+case,env=environment('main'))
   record['evaluation_status']=json.loads(ev.read_text()) if ev.exists() else dict(status='INCOMPLETE',error='evaluation ended before status record')
   if r['W']==16 and r['seed']==0:
    dp=BASE/'work/stage3-diagnostics'/case/'status.json'
    if not dp.exists():run_case([sys.executable,'-B','scripts/diagnose_t23.py',str(p)],'stage3-diag-'+case,env=environment('main'))
    record['diagnostic_status']=json.loads(dp.read_text()) if dp.exists() else dict(status='INCOMPLETE',error='diagnostic ended before status record')
   if r['scope']=='second batch' and r['method'] in P0+['B0','B1']:
    meta=next(m for m in json.loads((BASE/'logs/matrices-and-taus.json').read_text()) if m['matrix']==r['matrix']);record['post_cases']=[]
    for t in meta['taus']:
     pr=dict(record,tau=t['tau'],member=r['method']);pp=BASE/'work/stage3-post-catalog'/(case+'__tau'+str(t['tau'])+'.json');pp.parent.mkdir(exist_ok=True);pp.write_text(json.dumps(pr,ensure_ascii=False,indent=2));end=BASE/'work/post-e'/pp.stem/'record.json'
     if not end.exists():run_case([sys.executable,'-B','scripts/post_e_job.py',str(pp)],'stage3-post-'+pp.stem,env=environment('main'))
     record['post_cases'].append(str(end))
 record['controller_end']=time.time();result.write_text(json.dumps(record,ensure_ascii=False,indent=2));print(case,record['status'],round(time.time()-begin,1),flush=True);return record

if __name__=='__main__':
 assert (BASE/'delivery/round1-compare-20261106.receipt.json').exists(),'first delivery must be sealed and handed back before stage3';cases=catalog();(BASE/'logs/stage3-start.json').write_text(json.dumps(dict(start=time.time(),first_delivery_receipt=str(BASE/'delivery/round1-compare-20261106.receipt.json'),expected_cases=len(cases),method_limit_seconds=7200,queue_excluded=True),indent=2))
 gate=BASE/'logs/hp-repeated-cora-gate.json'
 if not gate.exists():
  records=[]
  for rep in [0,1]:
   if rep and records[0]['status']!='OK':break
   p=BASE/'work/stage3-generated'/('cora__C6-HP__W16__seed0'+(f'__repeat{rep}' if rep else '')+'.record.json')
   if not p.exists():run_case([sys.executable,'-B','scripts/external_hp.py','--matrix','cora','--rep',str(rep)],f'stage3-hp-cora-repeat{rep}',env=environment('hp'))
   records.append(json.loads(p.read_text()) if p.exists() else dict(status='INCOMPLETE',error='HP Cora gate ended before final record'))
  passed=len(records)==2 and all(r['status']=='OK' for r in records) and records[0]['sha256']==records[1]['sha256'];gate.write_text(json.dumps(dict(passed=passed,checks=records,same_seed=0),indent=2))
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:records=list(ex.map(run,cases))
 (BASE/'logs/stage3-run-complete.json').write_text(json.dumps(dict(ended=time.time(),cases=len(records),counts={s:sum(r['status']==s for r in records) for s in ['OK','INCOMPLETE','SKIPPED']}),indent=2))
