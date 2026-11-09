import ctypes as C,random,time,json
from pathlib import Path
import numpy as np
from native import BASE,I,L,ip,lp,Layout,chunks
LIB=C.CDLL(str(BASE/'work/t21/librq2-v8.dylib'));P=C.c_void_p
LIB.rq_graph.argtypes=[C.c_int,L,I];LIB.rq_graph.restype=P;LIB.rq_free_graph.argtypes=[P]
LIB.rq_ls.argtypes=[P,I,C.c_int,C.c_int];LIB.rq_ls.restype=P;LIB.rq_ls_sweep.argtypes=[P,I,C.c_int,C.c_double];LIB.rq_ls_sweep.restype=C.c_int
LIB.rq_ls_get.argtypes=[P,I,L];LIB.rq_free_ls.argtypes=[P]
def local_search(m,order,W=16,tau=None,lam=0.,seed=0,checkpoint=None):
 n=m.n;K=(sum(m.deg>tau)+W-1)//W if tau is not None else (n+W-1)//W;NB=(n+W-1)//W;words=(K+63)//64;CWords=(n+63)//64
 estimate=n*words*8+K*NB*2+K*CWords*16+NB*words*16+int(m.p[-1])*48+K*1024
 if estimate>8*2**30:raise RuntimeError(f'LS exact workspace preflight estimate {estimate} bytes exceeds frozen 8GiB safety budget')
 graph=LIB.rq_graph(n,lp(m.p),ip(m.c));arr=np.asarray(order,np.int32);state=LIB.rq_ls(graph,ip(arr),W,-1 if tau is None else tau);movable=list(range(n)) if tau is None else list(set(v for v in order if m.deg[v]>tau));rng=random.Random(seed);history=[];t=time.time()
 try:
  for sweep in range(10):
   vertices=movable[:];rng.shuffle(vertices);seq=np.asarray(vertices,np.int32);accepted=LIB.rq_ls_sweep(state,ip(seq),len(seq),lam);out=np.empty(n,np.int32);ug=np.empty(2,np.int64);LIB.rq_ls_get(state,ip(out),lp(ug));history.append(dict(sweep=sweep,accepted=accepted,sumU=int(ug[0]),sumGamma=int(ug[1]),elapsed=time.time()-t));print('LS',history[-1],flush=True)
   if checkpoint:
    cp=Path(checkpoint);tmp=cp.with_suffix('.tmp');tmp.write_text(json.dumps(dict(row_perm=out.tolist(),history=history,tau=tau,W=W,seed=seed,lam=lam,tracked_sumU=int(ug[0]),tracked_sumGamma=int(ug[1]),status='INCOMPLETE',note='last completed sweep checkpoint; final full recomputation not yet performed'),separators=(',',':')));tmp.replace(cp)
   if accepted==0:break
  order=out.tolist();assert np.array_equal(np.sort(out),np.arange(n));kept=order if tau is None else [v for v in order if m.deg[v]>tau];lc=Layout(m,chunks(kept,W),W);metrics=lc.metrics(order);lc.close();assert metrics['sumU']==int(ug[0]) and metrics['sumGamma']==int(ug[1]),(metrics,ug.tolist())
  return order,dict(history=history,sweeps_done=len(history),accepted_swaps=sum(h['accepted'] for h in history),tracked_sumU=int(ug[0]),tracked_sumGamma=int(ug[1]),independent_full_recompute=metrics,incremental_invariant_passed=True,workspace_preflight_bytes=int(estimate))
 finally:LIB.rq_free_ls(state);LIB.rq_free_graph(graph)
