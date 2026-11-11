import ctypes as C,hashlib,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from native import BASE,Matrix,I,L,ip,lp,chunks
from evaluate_t23 import read_order
from guard_provenance import classify_failure, is_failure_candidate
LIB=C.CDLL(str(BASE/'work/libguard-count.dylib'))
LIB.count_guard_windows.argtypes=[C.c_int,L,I,I,L,C.c_int,I,C.c_int,C.c_int]
LIB.count_guard_windows.restype=C.c_int64
def count(m,windows,D):
 flat=np.asarray([v for w in windows for v in w],np.int32);wp=np.asarray([0]+list(np.cumsum([len(w) for w in windows])),np.int64);res=np.asarray(D,np.int32)
 return int(LIB.count_guard_windows(m.n,lp(m.p),ip(m.c),ip(flat),lp(wp),len(windows),ip(res),len(res),400))
def gate():
 n=640;adj=[list(range(32,433)) if i==0 else list(range(32,432)) if i==16 else [] for i in range(n)]
 p=np.asarray([0]+list(np.cumsum([len(x) for x in adj])),np.int64);m=SimpleNamespace(n=n,p=p,c=np.asarray([v for a in adj for v in a],np.int32));assert count(m,[list(range(16)),list(range(16,32))],list(range(32,n)))==1
 checks=[];m=Matrix('cora');pi=list(range(m.n))
 for tau in [2,3]:
  D=[v for v in pi if m.deg[v]<=tau];windows=chunks([v for v in pi if m.deg[v]>tau]);expected=sum(len({int(c) for r in w for c in m.c[m.p[r]:m.p[r+1]]}&set(D))>400 for w in windows);actual=count(m,windows,D);assert actual==expected==0;checks.append(dict(matrix='cora',tau=tau,count=actual))
 m=Matrix('reddit');pi=list(range(m.n));rows=json.loads((BASE/'work/stage3-evaluations/stage3-reddit__B0__W16__seed0/rows.json').read_text())
 for row in rows:
  if row['diag']=='A0' and row['placement']=='tail-co' and row['d_rule']=='own' and 'co_chain_guard_windows_skipped' in row:
   tau=int(row['tau']);D=[v for v in pi if m.deg[v]<=tau];actual=count(m,chunks([v for v in pi if m.deg[v]>tau]),D);assert actual==row['co_chain_guard_windows_skipped'];checks.append(dict(matrix='reddit',tau=tau,count=actual,identical_to_successful_native_chain=True))
 result=dict(passed=True,synthetic_400_vs_401=True,checks=checks,source_sha256=hashlib.sha256((BASE/'scripts/guard_count.cpp').read_bytes()).hexdigest(),binary_sha256=hashlib.sha256((BASE/'work/libguard-count.dylib').read_bytes()).hexdigest());(BASE/'logs/stage3-guard-recovery-gate.json').write_text(json.dumps(result,indent=2));print('GUARD_RECOVERY_GATE_OK',checks)
def run():
 assert json.loads((BASE/'logs/stage3-guard-recovery-gate.json').read_text())['passed'];items=[];recovered=[];inherited=[];unproven=[];checks=0;cache={};mask_sizes={};command_cache={}
 cases=json.loads((BASE/'logs/stage3-planned-cases.json').read_text());meta={m['matrix']:m for m in json.loads((BASE/'logs/matrices-and-taus.json').read_text())};matrix=None;m=None
 def recover_failure(rows,index,number,base,rows_path,command_path):
  if not is_failure_candidate(rows[index]):return
  if matrix not in mask_sizes:mask_sizes[matrix]={int(t['tau']):int(np.count_nonzero(m.deg<=int(t['tau']))) for t in meta[matrix]['taus']}
  command_key=str(command_path)
  if command_key not in command_cache:command_cache[command_key]=json.loads(command_path.read_text()) if command_path.exists() else {}
  provenance=classify_failure(rows,index,command_cache[command_key],mask_sizes[matrix])
  row=rows[index];entry=dict(base,diag=int(row['diag'][-1]),placement='tail-co',d_rule='own',original_status=row['status'],rows_path=str(rows_path),rows_sha256=hashlib.sha256(rows_path.read_bytes()).hexdigest(),command_path=command_key,command_sha256=hashlib.sha256(command_path.read_bytes()).hexdigest() if command_path.exists() else None,**provenance)
  category=provenance['guard_scan_execution']
  if category=='executed_scan_recovered':entry.update(co_chain_guard_windows_skipped=number,guard_count_source='independent CSR count; byte-verified producer/native flow proves a completed cold guard scan before the observed pair-map error');recovered.append(entry)
  elif category=='inherited_failure_cache_count':entry.update(co_chain_guard_windows_skipped=number,guard_count_source='independent CSR count inherited from the earlier same-incidence failed scan identified by cache_origin_row_index; this condition did not execute a new native guard scan');inherited.append(entry)
  else:entry.update(structural_guard_windows=number,guard_count_source='structural eligibility only; execution/cache provenance unproven');unproven.append(entry)
 for case in cases:
  rp=BASE/'work/stage3-cases'/case['case_id']/'record.json'
  if not rp.exists():continue
  rec=json.loads(rp.read_text());path=rec.get('runtime_path');rows_path=BASE/'work/stage3-evaluations'/case['case_id']/'rows.json'
  if rec['status']!='OK' or not path or not rows_path.exists():continue
  if matrix!=case['matrix']:matrix=case['matrix'];m=Matrix(matrix)
  pi=read_order(path);assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==rec['sha256'];rows=json.loads(rows_path.read_text())
  for t in meta[matrix]['taus']:
   tau=t['tau']
   if case.get('main_tau_only') and t!=meta[matrix]['taus'][-1]:continue
   key=(matrix,rec['sha256'],case['W'],tau)
   if key not in cache:
    D=[v for v in pi if m.deg[v]<=tau];windows=chunks([v for v in pi if m.deg[v]>tau],case['W']);cache[key]=count(m,windows,D)
   number=cache[key];items.append(dict(case_id=case['case_id'],matrix=matrix,member=case['method'],W=case['W'],seed=case['seed'],tau=tau,order_sha256=rec['sha256'],structural_guard_windows=number,note='fixed A0 residual set; A1 self edges touch K columns only, so D coverage is unchanged'))
   for index,row in enumerate(rows):
    if str(row['tau'])!=str(tau) or row['placement']!='tail-co':continue
    if 'co_chain_guard_windows_skipped' in row:assert row['co_chain_guard_windows_skipped']==number;checks+=1
    elif is_failure_candidate(row):
     recover_failure(rows,index,number,dict(matrix=matrix,member=case['method'],W=case['W'],seed=case['seed'],tau=tau,source='own'),rows_path,BASE/'logs'/('stage3-eval-'+case['case_id']+'.command.json'))
 for item in items:item['source']='own'
 known_cases={c['case_id'] for c in cases}
 for folder in ['post-e','stage3-partial-post']:
  for rp in sorted((BASE/'work'/folder).glob('stage3-*/record.json')):
   if rp.parent.name.rsplit('__tau',1)[0] not in known_cases:continue
   pr=json.loads(rp.read_text());path=pr.get('order_path');rows_path=rp.parent/'rows.json'
   if not path or not rows_path.exists():continue
   name=pr['matrix'];tau=int(pr['tau']);W=int(pr.get('W',16));h=hashlib.sha256(Path(path).read_bytes()).hexdigest();assert h==pr['sha256']
   if matrix!=name:matrix=name;m=Matrix(matrix)
   pi=read_order(path);key=(matrix,h,W,tau)
   if key not in cache:
    D=[v for v in pi if m.deg[v]<=tau];cache[key]=count(m,chunks([v for v in pi if m.deg[v]>tau],W),D)
   number=cache[key];items.append(dict(case_id=rp.parent.name,matrix=matrix,member=pr['member'],W=W,seed=0,tau=tau,source='post-E',order_sha256=h,structural_guard_windows=number,partial=bool(pr.get('partial')),note='post-E actual saved order; structural eligibility only unless an executed guard scan is proven below'))
   rows=json.loads(rows_path.read_text())
   for index,row in enumerate(rows):
    if 'co_chain_guard_windows_skipped' in row:assert row['co_chain_guard_windows_skipped']==number;checks+=1
    elif is_failure_candidate(row):
     prefix='stage3-post-' if folder=='post-e' else 'stage3-partial-'
     recover_failure(rows,index,number,dict(matrix=matrix,member=pr['member'],W=W,seed=0,tau=tau,source='post-E'),rows_path,BASE/'logs'/(prefix+rp.parent.name+'.command.json'))
 result=dict(passed=True,successful_native_counts_checked=checks,structural_counts=items,recovered_actual_guard_counts=recovered,recovered_cached_guard_counts=inherited,unproven_failure_guard_candidates=unproven,note='Reported counts and physical scan execution are distinct. Successful saved counts are independently checked without asserting cold execution. Byte-identified cold failure scans are separated from inherited memoized failures; unknown sources remain structural-only. D-greedy failures before chain and process termination never imply guard execution. Scientific rows/statuses unchanged.')
 (BASE/'work/stage3-guard-recovery.json').write_text(json.dumps(result,indent=2));(BASE/'logs/stage3-guard-recovery-audit.json').write_text(json.dumps(dict(passed=True,successful_native_counts_checked=checks,structural_count_cases=len(items),recovered_count_cases=len(recovered),inherited_cached_count_cases=len(inherited),unproven_execution_cases=len(unproven)),indent=2));print('GUARD_RECOVERY_AUDIT_OK',checks,len(items),len(recovered),len(inherited),len(unproven));return result
if __name__=='__main__':
 import sys
 if '--audit' in sys.argv:
  from resource_slots import acquire
  slot=acquire();run()
 else:gate()
