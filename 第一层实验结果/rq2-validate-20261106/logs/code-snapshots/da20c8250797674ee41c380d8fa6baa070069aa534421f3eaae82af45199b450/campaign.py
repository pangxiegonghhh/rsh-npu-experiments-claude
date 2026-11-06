from __future__ import annotations
import argparse, ctypes as C, hashlib, itertools, json, math, os, pickle, sys, time, traceback
from pathlib import Path
sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[1]
REPO = Path("/Users/Zhuanz/.codex/visualizations/2026/11/05/01a1ac73-0f55-70c0-8e27-bb94bed5ad09/t21-rq2-20261106/repo")
REF = REPO / '第一层工作区/T17-空白一试算脚本'
os.environ['RQ2_HK'] = str(BASE/'work/selfcheck/rq2_hk_bin')
sys.path.insert(0, str(REF))
import rq2lib as ref
import methods
import numpy as np
from fast import FastGraph

OUT = BASE/'delivery/第一层实验结果/rq2-validate-20261106'
for sub in ('orders','tasks','checks'): (OUT/sub).mkdir(parents=True, exist_ok=True)
(BASE/'work/ordercache').mkdir(exist_ok=True)
P0 = ['B0','rsh-α0','rabbit-pilot','neutron-pilot','C9-Gorder','C9-S','C10-BP']
FIELDS = 'matrix diag member member_params W tau placement d_rule n k_windows resid_frac sumU meanU T sumGamma meanGamma sumR meanR R_p50 R_p90 R_max sumR_minus_Gamma order_sec d_sec status note'.split()
JOINT_FIELDS = FIELDS + ['start','lambda','mnc','seed','sweeps_done','accepted_swaps']

def slug(s: str) -> str: return s.replace('α','alpha').replace('β','beta').replace('/','_')
def dump(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'))); tmp.replace(path)
def digest(value: object) -> str: return hashlib.sha256(json.dumps(value,separators=(',',':')).encode()).hexdigest()
def acquisition() -> dict:
    return {d['matrix']:d for d in json.loads((BASE/'logs/input-acquisition.json').read_text())}
def load_adj(matrix: str) -> list[set[int]]:
    cache = BASE/'work'/f'{matrix}-A0.pickle'
    if cache.exists(): return pickle.loads(cache.read_bytes())
    entry = acquisition()[matrix]; n, adj = ref.load_mtx(entry['mtx'])
    temp=cache.with_suffix('.tmp');temp.write_bytes(pickle.dumps(adj,protocol=5));temp.replace(cache)
    return adj
def split(order: list[int], adj: list[set[int]], W: int, tau: int | None) -> tuple[list[list[int]],list[int],list[int]]:
    kept = [v for v in order if tau is None or len(adj[v]) > tau]
    resid = [v for v in order if tau is not None and len(adj[v]) <= tau]
    return [kept[i:i+W] for i in range(0,len(kept),W)], kept, resid
def evaluate(order: list[int], adj: list[set[int]], W: int, tau: int | None, placement: str, diag: str, columns: list[int] | None = None) -> dict:
    windows, kept, resid = split(order,adj,W,tau)
    colorder = columns if columns is not None else (order if tau is None or placement=='inplace' else kept+resid)
    pos = [0]*len(order)
    for i,v in enumerate(colorder):pos[v]=i
    Us=[];Gs=[];Rs=[]
    for window in windows:
        cols=set().union(*(adj[v] for v in window))
        if diag=='A1':cols.update(window)
        p=sorted(pos[c] for c in cols)
        Us.append(len(p));Gs.append(len({c//W for c in p}));Rs.append(1+sum(y!=x+1 for x,y in zip(p,p[1:])) if p else 0)
    k=len(windows);r=sorted(Rs)
    return {'n':len(order),'k_windows':k,'resid_frac':len(resid)/len(order),'sumU':sum(Us),'meanU':sum(Us)/k if k else 0.,
            'T':sum((u+15)//16 for u in Us),'sumGamma':sum(Gs),'meanGamma':sum(Gs)/k if k else 0.,
            'sumR':sum(Rs),'meanR':sum(Rs)/k if k else 0.,'R_p50':r[min(k-1,int(.5*k))] if k else 0,
            'R_p90':r[min(k-1,int(.9*k))] if k else 0,'R_max':max(r,default=0),'sumR_minus_Gamma':sum(Rs)-sum(Gs)}
def save_order(matrix: str, member: str, order: list[int], W: int, tau: int | None, rule: str, columns: list[int] | None = None, extra: dict | None = None) -> str:
    assert sorted(order)==list(range(len(order)))
    if columns is not None:assert sorted(columns)==list(range(len(order)))
    name=f'{matrix}__{slug(member)}__W{W}__tau{tau}__{rule}__{digest([order,columns])[:12]}.json'
    data={'matrix':matrix,'member':member,'W':W,'tau':tau,'d_rule':rule,'row_perm':order,'generated_on':'A0','residual_rule':'deg_A0 <= tau'}
    if columns is not None:data['col_perm']=columns
    if extra:data.update(extra)
    path=OUT/'orders'/name
    if not path.exists():dump(path,data)
    return 'orders/'+name
def order_for(matrix: str, member: str, W: int, graph: FastGraph) -> tuple[list[int],float,dict]:
    effective_W=W if member in ('C9-Gorder','C9-S','C10-BP','neutron-pilot') or member.startswith('C9-beta') else 16
    cache=BASE/'work/ordercache'/f'{matrix}__{slug(member)}__W{effective_W}.json'
    if cache.exists():d=json.loads(cache.read_text());return d['order'],d['sec'],d['params']
    t=time.perf_counter();params={'source_commit':'fd1fc09253b086daf394aa6e9c921faa59ae7569','computed_on':'A0'}
    if member=='B0':o=list(range(graph.n));params['source']='identity'
    elif member in ('rsh-α0','rabbit-pilot','neutron-pilot'):
        key={'rsh-α0':'rsh','rabbit-pilot':'rabbit','neutron-pilot':'neutron'}[member];o=graph.order(key,W)
        params.update(source='faithful C++ port of cora-pilot rsh_reorder_experiment.py',pilot_label=member,k=8,weighted_alpha=0,refine_passes=2,refine_span=8,cluster_windows=8)
    elif member=='C10-BP':o=graph.bp(W);params.update(source='C++ accelerated methods.bp, Python Random shuffle',seed=0,iters=20,W=W)
    elif member=='B-RCM-ref':o=methods.rcm(graph.adj);params.update(source='package-nine deterministic methods.rcm',tie_rule='(degree,index)')
    elif member=='SlashBurn':o=methods.slashburn(graph.adj);params.update(source='reference methods.slashburn',k=max(1,int(.005*graph.n)))
    else:
        beta=0. if member=='C9-S' else (float(member.removeprefix('C9-beta')) if member.startswith('C9-beta') else 1.)
        o=graph.order('gorder',W,beta);params.update(source='C++ port of methods.gorder',w=W-1,beta=beta,hub_skip='sqrt(n)',score='S_s + beta*S_n (reference S_n update = 2 per neighbor)')
    sec=time.perf_counter()-t;assert sorted(o)==list(range(graph.n));dump(cache,{'order':o,'sec':sec,'params':params})
    return o,sec,params

class Task:
    def __init__(self, key: str, matrix: str, member: str, params: dict, order_sec: float):
        self.key=key;self.matrix=matrix;self.member=member;self.params=params;self.order_sec=order_sec;self.rows=[];self.joint=[];self.checks=[]
    def flush(self) -> None:dump(OUT/'tasks'/(self.key+'.json'),{'rows':self.rows,'joint':self.joint,'checks':self.checks})
    def row(self, W: int, tau: int | None, placement: str, rule: str, diag: str, metrics: dict | None=None, sec: float=0., status: str='OK', note: str='', extra: dict | None=None) -> None:
        r=dict(matrix=self.matrix,diag=diag,member=self.member,member_params=json.dumps(self.params,ensure_ascii=False,separators=(',',':')),W=W,tau='none' if tau is None else tau,placement=placement,d_rule=rule,order_sec=self.order_sec,d_sec=sec,status=status,note=note)
        if metrics:r.update(metrics)
        self.rows.append(r)
        if extra:self.joint.append({**r,**extra})
        self.flush()
    def evaluate_conditions(self, order: list[int], adj: list[set[int]], W: int=16, taus: tuple=(None,2,3), exact: bool=True, only_tail: bool=False, extra: dict | None=None) -> None:
        for tau in taus:
            placements=['none'] if tau is None else (['tail'] if only_tail else ['inplace','tail'])
            before={}
            for placement in placements:
                path=save_order(self.matrix,self.member,order,W,tau,'own',extra=extra)
                for diag in ('A0','A1'):
                    e=evaluate(order,adj,W,tau,placement,diag)
                    self.row(W,tau,placement,'own',diag,e,note='order='+path,extra=extra)
                    if placement!='inplace':before[diag]=e
            placement='none' if tau is None else 'tail'
            if only_tail or not only_tail:
                for rule,intra in [('D-greedy','greedy')]+([('D-exact','exact')] if exact else []):
                    if rule=='D-exact' and self.matrix not in ('cora','dawson5','olafu'):
                        for diag in ('A0','A1'):self.row(W,tau,placement,rule,diag,status='SKIPPED',note='Plan §5: D-exact restricted to cora/dawson5/olafu for large k.',extra=extra)
                        continue
                    print(self.key, 'D start', W,tau,rule,flush=True)
                    t=time.perf_counter();new=ref.dstage(order,adj,W,tau,intra=intra);elapsed=time.perf_counter()-t
                    wa,ka,ra=split(order,adj,W,tau);wb,kb,rb=split(new,adj,W,tau)
                    canonical=lambda windows:sorted(tuple(sorted(w)) for w in windows)
                    assert canonical(wa)==canonical(wb) and ra==rb
                    if wa and len(wa[-1])<W:assert set(wa[-1])==set(wb[-1])
                    path=save_order(self.matrix,self.member,new,W,tau,rule,extra=extra)
                    for diag in ('A0','A1'):
                        e=evaluate(new,adj,W,tau,placement,diag);a=before[diag]
                        assert (a['sumU'],a['sumGamma'])==(e['sumU'],e['sumGamma']), (self.key,diag,tau,rule,a,e)
                        self.checks.append({'W':W,'tau':tau,'diag':diag,'rule':rule,'sumU_before_after':[a['sumU'],e['sumU']],'sumGamma_before_after':[a['sumGamma'],e['sumGamma']],'membership_unchanged':True,'residual_order_unchanged':True,'A0_A1_same_windows':True})
                        self.row(W,tau,placement,rule,diag,e,elapsed,note='order='+path+'; D generated on A0; A0 residual set fixed for A1',extra=extra)
                    print(self.key,'D done',W,tau,rule,round(elapsed,3),flush=True)

def independent_columns(order: list[int], adj: list[set[int]], W: int, rule: str) -> tuple[list[int] | None,str]:
    if rule=='indep-CBM':
        maximum=max(map(len,adj),default=0);lower_bound=maximum*(maximum-1)//2
        if lower_bound>50_000_000:
            return None,f'SKIPPED: distinct co pairs >= choose(max A0 degree={maximum},2) = {lower_bound} > 50000000; every pair of columns in this row co-occurs in its window.'
    windows,_,_=split(order,adj,W,None); cols=[set().union(*(adj[v] for v in w)) for w in windows]
    if rule=='indep-first':
        seen=set();out=[]
        for c in cols:
            for v in sorted(c):
                if v not in seen:seen.add(v);out.append(v)
        out.extend(v for v in range(len(adj)) if v not in seen);return out,'first occurrence by window; within-window original ID ascending'
    if rule=='indep-CBM':
        graph=FastGraph(adj)
        try:
            lib=C.CDLL(str(BASE/'work/libcbm.dylib'))
            from fast import I,L,ip
            lib.rq_cbm.argtypes=[C.c_int,L,I,I,C.c_int,C.c_int64,I,L];lib.rq_cbm.restype=C.c_int
            arr=np.asarray(order,dtype=np.int32);out=np.empty(len(order),dtype=np.int32);stats=np.empty(2,dtype=np.int64)
            rc=lib.rq_cbm(len(order),graph.indptr.ctypes.data_as(L),ip(graph.indices),ip(arr),W,50_000_000,ip(out),stats.ctypes.data_as(L))
            note=f'distinct_co_pairs={stats[0]}; pair_operations={stats[1]}; greedy edges sorted by (co,u,v) descending'
            if rc==1:return None,'SKIPPED: distinct co pairs > 50000000; '+note
            assert rc==0,rc
            return out.tolist(),note
        finally:graph.close()
    raise ValueError(rule)

def worker(spec: dict) -> None:
    assert json.loads((BASE/'logs/port-validation.json').read_text())['passed']
    matrix=spec['matrix'];adj=load_adj(matrix);graph=FastGraph(adj);kind=spec['kind'];member=spec['member'];W=spec.get('W',16)
    start=spec.get('start',member);o,sec,params=order_for(matrix,start,W,graph)
    task=Task(spec['key'],matrix,member,params,sec)
    try:
        if kind in ('p0','w','member'):
            task.evaluate_conditions(o,adj,W,taus=(None,3) if kind=='w' else (None,2,3),exact=(W==16))
        elif kind=='ls':
            assert json.loads((BASE/'logs/ls-validation.json').read_text())['passed']
            t=time.perf_counter();o,info=graph.ls(o,W,spec['tau'],spec['lambda'],spec['seed']);task.order_sec+=time.perf_counter()-t
            e=evaluate(o,adj,W,spec['tau'],'tail' if spec['tau'] is not None else 'none','A0')
            assert (e['sumU'],e['sumGamma'])==(info['tracked_sumU'],info['tracked_sumGamma'])
            task.params={**params,**spec,'ls_implementation':'sparse C++ MemberLS/MemberLSPart port', 'tie_rule':info['tie_rule'],'rng':info['rng']}
            task.checks.append({'ls_incremental_equals_full_recompute':True,'sumU':e['sumU'],'sumGamma':e['sumGamma'],'history':info['history']})
            extra={'start':start,'lambda':spec['lambda'],'seed':spec['seed'],'sweeps_done':info['sweeps_done'],'accepted_swaps':info['accepted_swaps']}
            task.evaluate_conditions(o,adj,W,taus=(None,2,3) if spec['tau'] is None else (spec['tau'],),exact=False,only_tail=True,extra=extra)
        elif kind=='independent':
            assert json.loads((BASE/'logs/cbm-validation.json').read_text())['passed']
            t=time.perf_counter();columns,note=independent_columns(o,adj,W,spec['rule']);elapsed=time.perf_counter()-t
            if columns is None:
                for diag in ('A0','A1'):task.row(W,None,'none',spec['rule'],diag,sec=elapsed,status='SKIPPED',note=note)
            else:
                path=save_order(matrix,member,o,W,None,spec['rule'],columns=columns)
                for diag in ('A0','A1'):task.row(W,None,'none',spec['rule'],diag,evaluate(o,adj,W,None,'none',diag,columns),elapsed,note=note+'; order='+path)
        task.flush()
    finally:graph.close()

if __name__=='__main__':
    spec=json.loads(Path(sys.argv[1]).read_text())
    try:worker(spec)
    except Exception:
        traceback.print_exc();raise
