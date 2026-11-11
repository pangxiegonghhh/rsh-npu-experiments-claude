import ctypes as C, hashlib, json, math, os, random
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parents[1]
I=C.POINTER(C.c_int32);L=C.POINTER(C.c_int64);D=C.POINTER(C.c_double);Q=C.POINTER(C.c_uint64)
def ip(a):return a.ctypes.data_as(I)
def lp(a):return a.ctypes.data_as(L)
class Matrix:
 def __init__(self,name):
  self.name=name;p=BASE/'work/matrices'/name
  self.p=np.load(p/'indptr.npy',mmap_mode='r');self.c=np.load(p/'indices.npy',mmap_mode='r');self.deg=np.diff(self.p);self.n=len(self.p)-1
 def adjacency(self):return [set(map(int,self.c[self.p[r]:self.p[r+1]])) for r in range(self.n)]
class Candidates:
 lib=C.CDLL(str(BASE/'work/libcandidates-v2.dylib'))
 lib.cand_graph.argtypes=[C.c_int,L,I];lib.cand_graph.restype=C.c_void_p
 lib.cand_free.argtypes=[C.c_void_p]
 lib.cand_order.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_int,Q,I,L,C.c_char_p]
 lib.cand_sizes.argtypes=[C.c_void_p,I]
 def __init__(self,m):self.m=m;self.ptr=self.lib.cand_graph(m.n,lp(m.p),ip(m.c))
 def close(self):
  if self.ptr:self.lib.cand_free(self.ptr);self.ptr=None
 def order(self,name,W=16,seed=0):
  methods={'C2-LSH':0,'C3-W1':1,'C3-W4':1,'C3-A':1,'C3-W4-noP':1,'C4-U':2,'C4-T':3,'C7-I':4}
  b=1 if name=='C3-W1' else (4 if name!='C3-A' or self.m.n<50000 else 32 if self.m.n<100000 else 128)
  P=(1<<61)-1;params=[]
  for k in range(128):
   h=lambda t:int.from_bytes(hashlib.sha256(f'C2-LSH|seed={seed}|k={k}|{t}'.encode()).digest()[:8],'big')
   params.extend([h('a')%(P-1)+1,h('b')%P])
  params=np.asarray(params,dtype=np.uint64);out=np.empty(self.m.n,np.int32);st=np.zeros(16,np.int64);err=C.create_string_buffer(1024)
  rc=self.lib.cand_order(self.ptr,methods[name],W,b,int(name!='C3-W4-noP'),params.ctypes.data_as(Q),ip(out),lp(st),err)
  if rc:raise RuntimeError(err.value.decode() or str(rc))
  assert np.array_equal(np.sort(out),np.arange(self.m.n))
  sizes=np.empty(int(st[11]),np.int32);self.lib.cand_sizes(self.ptr,ip(sizes));diag=dict(zip(['groups_full_before','short_before','P_merges','P_new_full','short_after','groups_cut_by_windows','groups','accelerated_comparisons_or_pairs','short_or_qualified','merged','rejected_capacity'],map(int,st)));diag['evaluation_group_sizes']=sizes.tolist();return out.tolist(),diag

class Layout:
 lib=C.CDLL(os.environ.get('RQ3_LAYOUT_LIB',str(BASE/'work/liblayouts-v2.dylib')))
 lib.lc_make.argtypes=[C.c_int,L,I,I,L,C.c_int,C.c_int,C.c_int];lib.lc_make.restype=C.c_void_p
 lib.lc_free.argtypes=[C.c_void_p];lib.lc_layout.argtypes=[C.c_void_p,I,I,C.c_int,C.c_int,C.c_int,I,L,C.c_char_p]
 lib.lc_metrics.argtypes=[C.c_void_p,I,L]
 def __init__(self,m,windows,W=16,diag=0):
  self.m=m;self.W=W;self.windows=windows;flat=np.asarray([v for w in windows for v in w],np.int32);wp=np.asarray([0]+list(np.cumsum([len(w) for w in windows])),np.int64)
  self.ptr=self.lib.lc_make(m.n,lp(m.p),ip(m.c),ip(flat),lp(wp),len(windows),W,diag)
 def close(self):
  if self.ptr:self.lib.lc_free(self.ptr);self.ptr=None
 def layout(self,pi,residual,rule='tail',d=True):
  pi=np.asarray(pi,np.int32);res=np.asarray(residual,np.int32);out=np.empty(self.m.n,np.int32);st=np.zeros(8,np.int64);err=C.create_string_buffer(1024)
  rc=self.lib.lc_layout(self.ptr,ip(pi),ip(res),len(res),{'tail':0,'tail-co':1,'inplace':2,'snap':3,'gap':4}[rule],int(d),ip(out),lp(st),err)
  if rc:raise RuntimeError(err.value.decode() or str(rc))
  assert np.array_equal(np.sort(out),np.arange(self.m.n)), 'layout permutation failed'
  return out.tolist(),{'co_chain_guard_windows_skipped':int(st[0])}
 def metrics(self,sigma):
  out=np.empty(9,np.int64);sig=np.asarray(sigma,np.int32);self.lib.lc_metrics(self.ptr,ip(sig),lp(out))
  result=dict(zip(['k_windows','sumU','T','sumGamma','sumR','R_p50','R_p90','R_max','write_runs_aic'],map(int,out)));result['meanR']=round(result['sumR']/result['k_windows'],6) if result['k_windows'] else 0
  return result

def chunks(seq,W=16,offset=0):return ([seq[:offset]] if offset else [])+[seq[i:i+W] for i in range(offset,len(seq),W)]
def write_runs(sigma,D):
 mask=set(D);p=[i for i,v in enumerate(sigma) if v in mask];return sum(i==0 or p[i]!=p[i-1]+1 for i in range(len(p)))

class Rect:
 lib=C.CDLL(str(BASE/'work/librect.dylib'))
 lib.rect_make.argtypes=[C.c_int,L,I,C.c_int,I];lib.rect_make.restype=C.c_void_p
 lib.rect_free.argtypes=[C.c_void_p];lib.rect_order.argtypes=[C.c_void_p,C.c_int,C.c_int,I]
 lib.rect_bp.argtypes=[C.c_void_p,I,C.c_int,C.c_int,C.c_int,D,I]
 def __init__(self,m,K):
  self.m=m;self.K=sorted(K);arr=np.asarray(self.K,np.int32);self.n=len(arr);self.ptr=self.lib.rect_make(m.n,lp(m.p),ip(m.c),self.n,ip(arr))
 def close(self):
  if self.ptr:self.lib.rect_free(self.ptr);self.ptr=None
 def order(self,method,W=16,seed=0):
  if method!='C10-BP':
   out=np.empty(self.n,np.int32);self.lib.rect_order(self.ptr,{'C9-Gorder':0,'C9-S':1,'rsh-α0':2,'rabbit-pilot':3,'neutron-pilot':4}[method],W,ip(out));return [self.K[i] for i in out]
  rng=random.Random(seed);logs=np.asarray([0.]+[math.log2(x) for x in range(1,self.m.n+2)],np.float64)
  def split(vertices):
   if len(vertices)<=W:return vertices
   size=len(vertices);s1=W*math.ceil(size/(2*W));vertices=vertices[:];rng.shuffle(vertices);arr=np.asarray(vertices,np.int32);side=np.empty(size,np.int32);self.lib.rect_bp(self.ptr,ip(arr),size,s1,20,logs.ctypes.data_as(D),ip(side))
   return split([v for i,v in enumerate(vertices) if side[i]==0])+split([v for i,v in enumerate(vertices) if side[i]==1])
  return [self.K[i] for i in split(list(range(self.n)))]
