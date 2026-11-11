import csv, hashlib, json, math, os, subprocess, sys, time
from pathlib import Path
import numpy as np

BASE=Path(__file__).resolve().parents[1]
OLD=Path('/Users/Zhuanz/.codex/visualizations/2026/11/05/01a1ac73-0f55-70c0-8e27-bb94bed5ad09/t22-t23-20261106')
REPO=Path('/Users/Zhuanz/ClaudeCode/rsh-npu-experiments-claude')
META=json.loads((BASE/'logs/matrices-and-taus.json').read_text())
HISTORY=list(csv.DictReader((REPO/'第一层实验结果/round1-compare-20261106/results.csv').open()))
STATE=dict(status='RUNNING',phase='baseline',orders=[],gates=[],scores={})
ENV=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')

def save():
    (BASE/'logs/progress.json').write_text(json.dumps(STATE,indent=2))

def command(cmd, key, timeout):
    start=time.time()
    with (BASE/'logs'/(key+'.stdout')).open('w') as out, (BASE/'logs'/(key+'.stderr')).open('w') as err:
        p=subprocess.Popen(cmd,stdout=out,stderr=err,env=ENV)
        try: rc=p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill();p.wait();rc=124
    log=dict(command=cmd,start=start,end=time.time(),rc=rc,timeout=timeout)
    (BASE/'logs'/(key+'.command.json')).write_text(json.dumps(log,indent=2))
    if rc: raise RuntimeError(f'{key}: rc={rc}; no retry')

def order(matrix, alpha=0, k=8, iso=0, tag='', c4=False):
    key=f'{matrix}__{"C4-U-calibration" if c4 else "B-RSH-ref"}__alpha={alpha:g},k={k},iso={"near" if iso else "tail"}{tag}'
    cmd=[sys.executable,'-B',str(BASE/'code/run_order.py'),matrix,str(alpha),str(k),str(iso),'--tag',tag]
    if c4:cmd+=['--c4']
    meta=next(x for x in META if x['matrix']==matrix)
    command(cmd,'order-'+key,3600 if meta['nnz_A0']>1e7 else 600)
    r=json.loads((BASE/'orders'/(key+'.record.json')).read_text())
    assert r['status']=='OK'
    STATE['orders'].append(r);save();print('ORDER OK',matrix,r['params'],round(r['seconds'],3),flush=True)
    return r

def read(path):
    d=json.loads(Path(path).read_text());return d['row_perm'] if isinstance(d,dict) else d

def evaluate(r):
    key=Path(r['path']).name.replace('.order.json','')
    folder=BASE/'evaluations'/key;folder.mkdir(exist_ok=True)
    rec=BASE/'orders'/(key+'.record.json')
    # Import and call the byte-identical T23 evaluator; keep its complete grid.
    cmd=[sys.executable,'-B','-c',
         'import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from memory_guard import ensure_limit;ensure_limit();from evaluate_t23 import evaluate;r=json.loads(Path(sys.argv[2]).read_text());p=Path(sys.argv[3]);s=evaluate(r,p);(p/"status.json").write_text(json.dumps(s));print(json.dumps(s))',
         str(BASE/'code'),str(rec),str(folder)]
    command(cmd,'eval-'+key,7200)
    return json.loads((folder/'rows.json').read_text())

def score(rows):
    ratios=[]
    for matrix in ['cora','ogbn-arxiv']:
        for tau in ['2','3']:
            row=next(x for x in rows if x['matrix']==matrix and x['diag']=='A0' and str(x['tau'])==tau and x['placement']=='tail-co' and x['d_rule']=='own')
            ref=next(x for x in HISTORY if x['matrix']==matrix and x['member']=='B0' and x['diag']=='A0' and x['tau']==tau and x['placement']=='tail-co' and x['d_rule']=='own' and x['source']=='own')
            assert row['status']=='OK'
            ratios.append(row['T']/int(ref['T']))
    return math.exp(sum(map(math.log,ratios))/4)

def pair(a,k,iso=0):
    rows=[]
    for m in ['cora','ogbn-arxiv']:
        key=(m,a,k,iso)
        if key not in CACHE:
            r=order(m,a,k,iso);CACHE[key]=(r,evaluate(r))
        rows+=CACHE[key][1]
    return score(rows),rows

def select(values, preference):
    best=min(values.values())
    return min((v for v,s in values.items() if s/best<1.005),key=preference)

CACHE={}
def main():
    save()
    references={
      'cora':next((OLD/'inputs/t21/orders').glob('cora__rsh-alpha0__W16__tauNone__own__60d4a3f802ea.json')),
      'ogbn-arxiv':next((OLD/'inputs/t21/orders').glob('ogbn-arxiv__rsh-alpha0__W16__tauNone__own__a6340c0d6c29.json')),
      'reddit':OLD/'work/stage3-generated/reddit__B1__W16__seed0.order.json',
      'ogbn-products':OLD/'remote-evidence/hostB-windows16gb-wsl2/t23-hostb-orders/work/stage3-generated/ogbn-products__B1__W16__seed0.order.json'}
    expected=['1c1889794c291f9afb95cb32263f13bc59969c9d2e77e3446296069b63e82a72','faff0625413a5d724bcbeceb937e9e504077a72b7fe109287ff143fe4e04aa82','c6d9e9e2348fde87329958ed6f79705c208b34dceaa53584d888582a5e1a368d','60b889c2506be67a272e3e75656d36d0ac09ae60d467a4f14336c7f6f65d05f7']
    for (m,ref),sha in zip(references.items(),expected):
        assert hashlib.sha256(ref.read_bytes()).hexdigest()==sha
        r=order(m); pi=read(r['path']); target=read(ref)
        diff=[i for i,(a,b) in enumerate(zip(pi,target)) if a!=b]
        gate=dict(matrix=m,reference=str(ref),reference_sha256=sha,identical=not diff,difference_positions=len(diff))
        rows=None
        if diff:
            deg=np.load(BASE/'work/matrices'/m/'degrees.npy')
            gate['empty_only']=all(deg[pi[i]]==0 and deg[target[i]]==0 for i in diff)
            assert m in ['cora','ogbn-arxiv'] and gate['empty_only'],gate
        if m in ['cora','ogbn-arxiv']:
            rows=evaluate(r);CACHE[(m,0,8,0)]=(r,rows)
            checks=[]
            for x in rows:
                refrow=next(y for y in HISTORY if y['matrix']==m and y['member']=='B1' and y['diag']==x['diag'] and y['W']=='16' and y['tau']==str(x['tau']) and y['placement']==x['placement'] and y['d_rule']==x['d_rule'] and y['source']=='own')
                checks.append(x['sumU']==int(refrow['sumU']) and x['T']==int(refrow['T']))
            gate['all_grid_sumU_T_identical']=all(checks)
            assert all(checks),gate
        STATE['gates'].append(gate);save();print('GATE OK',gate,flush=True)
    STATE['phase']='alpha sweep';save()
    alphas=[0,.125,.25,.5,.75,1.]
    av={a:pair(a,8)[0] for a in alphas}
    a=select(av,lambda a:a);STATE['scores']['alpha']=av;STATE['selected_alpha']=a;save()
    STATE['phase']='k sweep';save()
    kv={k:pair(a,k)[0] for k in [4,8,16]}
    k=select(kv,lambda k:(k!=8,abs(k-8),k))
    ratio=min(kv.values())/av[0]
    STATE.update(selected_k=k,early_stop_ratio=ratio,branch='NO' if ratio>.98 or (a,k)==(0,8) else 'YES')
    STATE['scores']['k']=kv;save();print('EARLY STOP',STATE['branch'],ratio,flush=True)
    STATE['phase']='E1';save()
    near,nearrows=pair(a,k,1);_,tailrows=pair(a,k)
    comparisons=[]
    for x in nearrows:
        if x['tau']=='none' or x['placement']!='tail-co' or x['d_rule']!='own':continue
        y=next(y for y in tailrows if all(y[z]==x[z] for z in ['matrix','diag','tau','placement','d_rule']))
        comparisons.append(dict(matrix=x['matrix'],diag=x['diag'],tau=x['tau'],near_T=x['T'],tail_T=y['T'],not_worse=x['T']<=y['T']))
    STATE['E1']=dict(comparisons=comparisons,H4=sum(x['not_worse'] for x in comparisons)/len(comparisons)>=2/3)
    rr=order('cora',a,k,tag='__determinism')
    STATE['determinism_passed']=rr['sha256']==CACHE[('cora',a,k,0)][0]['sha256'];assert STATE['determinism_passed'];save()
    STATE['phase']='C4-U calibration';save()
    for m in [x['matrix'] for x in META if x['matrix']!='ogbn-products']:order(m,c4=True)
    if STATE['branch']=='YES':
        STATE.update(status='EXTENSION_REQUIRED',phase='third-round and validation pending');save();return
    STATE.update(status='COMPLETED_NO_BRANCH',phase='analysis and sealing');save()

if __name__=='__main__':
    try:main()
    except Exception as e:
        import traceback
        STATE.update(status='INCOMPLETE',error=str(e),traceback=traceback.format_exc());save();raise
