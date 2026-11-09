import ctypes as C
import numpy as np
from native import BASE,I,L,ip,lp
LIB=C.CDLL(str(BASE/'work/libc1-forest.dylib'));LIB.c1_forest.argtypes=[C.c_int,L,I,I,C.c_int,C.c_int,I,L]
def order(a,neighbors,variant):
 p=np.asarray(a.indptr,np.int64);c=np.asarray(a.indices,np.int32);nn=np.asarray(neighbors,np.int32);out=np.empty(a.shape[0],np.int32);stats=np.zeros(3,np.int64);LIB.c1_forest(a.shape[0],lp(p),ip(c),ip(nn),nn.shape[1],variant=='H',ip(out),lp(stats));return out.tolist(),dict(zip(['graph_components','graph_edges','zero_distance_edges'],map(int,stats)))
