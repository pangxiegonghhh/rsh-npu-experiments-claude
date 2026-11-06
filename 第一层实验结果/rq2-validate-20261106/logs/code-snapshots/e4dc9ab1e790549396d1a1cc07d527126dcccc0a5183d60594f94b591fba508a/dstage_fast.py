from __future__ import annotations
import ctypes as C
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[1]
LIB=C.CDLL(str(BASE/'work/libdstage.dylib'))
I=C.POINTER(C.c_int32);L=C.POINTER(C.c_int64)
LIB.rq_dstage.argtypes=[C.c_int,L,I,I,C.c_int,C.c_int,C.c_int,I,L];LIB.rq_dstage.restype=C.c_int
def dstage(order:list[int],adj:list[set[int]],W:int=16,tau:int|None=None,intra:str='exact')->list[int]:
    ptr=np.zeros(len(adj)+1,dtype=np.int64);ptr[1:]=np.cumsum([len(x) for x in adj])
    idx=np.fromiter((x for row in adj for x in row),dtype=np.int32,count=int(ptr[-1]));arr=np.asarray(order,dtype=np.int32);out=np.empty(len(adj),dtype=np.int32);stats=np.empty(4,dtype=np.int64)
    ip=lambda a:a.ctypes.data_as(I)
    rc=LIB.rq_dstage(len(adj),ptr.ctypes.data_as(L),ip(idx),ip(arr),W,-1 if tau is None else tau,int(intra=='exact'),ip(out),stats.ctypes.data_as(L));assert rc==0
    return out.tolist()
