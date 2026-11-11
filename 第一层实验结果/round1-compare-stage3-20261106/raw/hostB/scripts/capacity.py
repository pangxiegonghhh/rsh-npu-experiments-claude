import ctypes as C,json,time
import numpy as np
from native import BASE,I,L,ip,lp
LIB=C.CDLL(str(BASE/'work/librepair.dylib'));LIB.capacity_repair.argtypes=[C.c_int,L,I,C.c_int,C.c_int,I,I,L]
def repair(m,labels,W):
 labels=np.asarray(labels,np.int32);k=(sum(m.deg>0)+W-1)//W;initial=labels.copy();trace=np.empty((m.n,4),np.int32);stats=np.empty(4,np.int64);start=time.time();rc=LIB.capacity_repair(m.n,lp(m.p),ip(m.c),k,W,ip(labels),ip(trace),lp(stats));assert rc==0,rc
 groups=[[] for _ in range(k)];em=[]
 for r,g in enumerate(labels):(em if g<0 else groups[g]).append(r)
 order=[v for group in groups for v in group]+em;assert sorted(order)==list(range(m.n));return order,dict(pre_objective_sumU=int(stats[0]),post_objective_sumU=int(stats[1]),moves=int(stats[2]),recomputed_post_objective=int(stats[3]),repair_seconds=time.time()-start,trace=trace[:stats[2]].tolist(),initial_labels=initial.tolist(),repaired_labels=labels.tolist(),target_sizes=[len(g) for g in groups])
