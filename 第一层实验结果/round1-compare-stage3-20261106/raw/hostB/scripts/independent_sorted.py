import ctypes as C,json
import numpy as np
from native import BASE,I,L,ip,lp
LIB=C.CDLL(str(BASE/'work/libindependent-sorted.dylib'));LIB.independent_sorted.argtypes=[C.c_int,L,I,I,L,C.c_int,I,C.c_int,C.c_int,L]
def metrics(m,windows,sigma,W=16,diag=0):
 flat=np.asarray([v for w in windows for v in w],np.int32);ptr=np.asarray([0]+list(np.cumsum([len(w) for w in windows])),np.int64);s=np.asarray(sigma,np.int32);out=np.zeros(9,np.int64);LIB.independent_sorted(m.n,lp(m.p),ip(m.c),ip(flat),lp(ptr),len(windows),ip(s),W,diag,lp(out));return dict(zip(['k_windows','sumU','T','sumGamma','sumR','R_p50','R_p90','R_max','write_runs_aic'],map(int,out)))
