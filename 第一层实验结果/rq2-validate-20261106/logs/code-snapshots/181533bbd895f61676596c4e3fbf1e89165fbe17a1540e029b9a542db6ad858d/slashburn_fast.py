from __future__ import annotations
import ctypes as C
import numpy as np
from fast import BASE,FastGraph,I,L,ip
LIB=C.CDLL(str(BASE/'work/libslashburn.dylib'))
LIB.rq_slashburn.argtypes=[C.c_int,L,I,C.c_int,I,I]
def reorder(graph:FastGraph,k:int|None=None)->list[int]:
    k=k or max(1,int(.005*graph.n));out=np.empty(graph.n,dtype=np.int32);sizes=np.empty(2,dtype=np.int32)
    LIB.rq_slashburn(graph.n,graph.indptr.ctypes.data_as(L),ip(graph.indices),k,ip(out),ip(sizes))
    front,tail=map(int,sizes);gcc=out[front:front+tail].tolist()
    # Preserve the reference's final Python-set iteration as the stable degree tie order.
    result=out[:front].tolist()+sorted(set(gcc),key=lambda v:-len(graph.adj[v]))+out[front+tail:].tolist()
    assert len(result)==graph.n and sorted(result)==list(range(graph.n))
    return result
