from __future__ import annotations
import ctypes as C
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[1]
LIB=C.CDLL(str(BASE/'work/libmetrics.dylib'))
I=C.POINTER(C.c_int32);L=C.POINTER(C.c_int64)
LIB.rq_metrics.argtypes=[C.c_int,L,I,I,C.c_int,C.c_int,C.c_int,C.c_int,I,C.c_int,L];LIB.rq_metrics.restype=C.c_int
def evaluate(graph,order:list[int],W:int,tau:int|None,placement:str,diag:str,columns:list[int]|None=None)->dict:
    arr=np.asarray(order,dtype=np.int32);col=np.asarray(columns if columns is not None else [],dtype=np.int32);out=np.empty(11,dtype=np.int64);ip=lambda a:a.ctypes.data_as(I)
    rc=LIB.rq_metrics(graph.n,graph.indptr.ctypes.data_as(L),ip(graph.indices),ip(arr),W,-1 if tau is None else tau,int(placement=='inplace'),int(diag=='A1'),ip(col),int(columns is not None),out.ctypes.data_as(L));assert rc==0
    n,k,resid,U,T,G,R,p50,p90,maximum,diff=map(int,out)
    return dict(n=n,k_windows=k,resid_frac=resid/n,sumU=U,meanU=U/k if k else 0.,T=T,sumGamma=G,meanGamma=G/k if k else 0.,sumR=R,meanR=R/k if k else 0.,R_p50=p50,R_p90=p90,R_max=maximum,sumR_minus_Gamma=diff)
