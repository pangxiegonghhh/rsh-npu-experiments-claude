import ctypes as C, numpy as np, sys, math, importlib.util, hashlib
# T4 派发：rect_t4.cpp 在 cora 上的自检（审核环境 2026-11-11 已跑通，见说明 §2）
# 用法: python3 -I -B check_rect_t4_cora.py <仓库根目录> <库目录>
#   库目录里须有原版 librect.(so|dylib) 与新版 librect-t4.(so|dylib)
import os
REPO=sys.argv[1]; W=sys.argv[2]
EXT='dylib' if os.path.exists(os.path.join(W,'librect-t4.dylib')) else 'so'
L=C.POINTER(C.c_int64); I=C.POINTER(C.c_int32)
def load(name):
    lib=C.CDLL(f'{W}/{name}'); lib.rect_make.argtypes=[C.c_int,L,I,C.c_int,I]; lib.rect_make.restype=C.c_void_p
    lib.rect_free.argtypes=[C.c_void_p]; lib.rect_order.argtypes=[C.c_void_p,C.c_int,C.c_int,I]; return lib
orig=load(f'librect.{EXT}'); t4=load(f'librect-t4.{EXT}')
t4.rect_order_rsh.argtypes=[C.c_void_p,C.c_double,C.c_int,C.c_int,I]
t4.rect_last_local_isolated.argtypes=[C.c_void_p]; t4.rect_last_local_isolated.restype=C.c_long
t4.rect_last_moved.argtypes=[C.c_void_p]; t4.rect_last_moved.restype=C.c_long
# cora A0
hdr=None; pr=[]
for line in open(REPO+'/第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx'):
    if line.startswith('%'): continue
    p=line.split()
    if hdr is None: hdr=int(p[0]); continue
    pr.append((int(p[0])-1,int(p[1])-1))
n=hdr; ent=[set() for _ in range(n)]
for r,c in pr:
    if r!=c: ent[r].add(c); ent[c].add(r)
indptr=np.zeros(n+1,np.int64); indptr[1:]=np.cumsum([len(e) for e in ent])
idx=np.fromiter((c for e in ent for c in sorted(e)),np.int32,count=int(indptr[-1]))
K=np.asarray([v for v in range(n) if ent[v]],np.int32)
def mk(lib): return lib.rect_make(n,indptr.ctypes.data_as(L),idx.ctypes.data_as(I),len(K),K.ctypes.data_as(I))
def run_orig():
    g=mk(orig); out=np.empty(len(K),np.int32); orig.rect_order(g,2,16,out.ctypes.data_as(I)); orig.rect_free(g); return [int(K[i]) for i in out]
def run_t4(a,k,iso):
    g=mk(t4); out=np.empty(len(K),np.int32); t4.rect_order_rsh(g,a,k,iso,out.ctypes.data_as(I))
    li,mv=t4.rect_last_local_isolated(g),t4.rect_last_moved(g); t4.rect_free(g); return [int(K[i]) for i in out],li,mv
sup=[frozenset(e) for e in ent]; nz=[len(e) for e in ent]
def T_part(order,tau,Wd=16):
    Kp=[r for r in order if nz[r]>tau]; D=[r for r in order if nz[r]<=tau]; pos={r:i for i,r in enumerate(Kp+D)}; T=0
    for s in range(0,len(Kp),Wd):
        cols=set()
        for r in Kp[s:s+Wd]: cols.update(pos[c] for c in sup[r])
        T+=math.ceil(len(cols)/16)
    return T
B0=list(range(n)); base={t:T_part(B0,t) for t in (2,3)}
def gm(order): return math.exp(sum(math.log(T_part(order,t)/base[t]) for t in (2,3))/2)
h=lambda o: hashlib.sha256(','.join(map(str,o)).encode()).hexdigest()[:12]
# Python 先导
spec=importlib.util.spec_from_file_location('pilot',REPO+'/第一层实验结果/cora-pilot-20261104/rsh_reorder_experiment.py')
m=importlib.util.module_from_spec(spec); sys.modules['pilot']=m; spec.loader.exec_module(m)
M=m.SparseMatrix(n_rows=n,n_cols=n,entries=[[(c,1.0) for c in sorted(e)] for e in ent])
py=lambda a,k: m.rsh_reorder(M,k=k,weighted_alpha=a)[0]
o_orig=run_orig(); o_t4,_,_=run_t4(0.0,8,0); o_py=py(0.0,8)
print(f"[门1] 原版 rsh() 与 rsh_t4(0,8,tail) 逐位相同：{o_orig==o_t4}   哈希 {h(o_orig)} / {h(o_t4)}")
print(f"      与 Python 先导 α=0 逐位相同：{o_orig==o_py}   几何均值 {gm(o_orig):.4f}（先导 0.7044）")
print(f"{'α':>6}{'k':>4}{'iso':>5}  {'几何均值':>8} {'相对B1':>7}  局部孤立/移动  与Python同序")
b=gm(o_orig)
for a,k in [(0.125,8),(0.25,8),(0.5,8),(1.0,8),(0.0,4),(0.0,16),(0.0,32)]:
    o,li,mv=run_t4(a,k,0); same=(o==py(a,k))
    print(f"{a:>6}{k:>4}{'tail':>5}  {gm(o):8.4f} {gm(o)/b:7.4f}  {li:>4}/{mv:<4}   {same}")
o16,_,_=run_t4(0.0,16,0); o32,_,_=run_t4(0.0,32,0); print(f"[门3] k=16 与 k=32 行序相同：{o16==o32}（审核环境曾验为相同）")
o2,_,_=run_t4(0.25,8,0); print(f"[门2] 确定性：α=0.25 连跑两次相同：{o2==run_t4(0.25,8,0)[0]}")
for a in (0.0,0.25):
    oi,li,mv=run_t4(a,8,1); ot,_,_=run_t4(a,8,0)
    print(f"[E1] α={a} iso=near：局部孤立 {li}、移动 {mv}；行序与 tail 不同：{oi!=ot}；几何均值 near {gm(oi):.4f} / tail {gm(ot):.4f}（相对 {gm(oi)/gm(ot):.4f}）；仍为置换：{sorted(oi)==list(range(n))}")

ok=True
def chk(name,cond):
    global ok; ok&=bool(cond); print(f"  {'PASS' if cond else 'FAIL'}  {name}")
print("== 判定 ==")
chk("门1：rsh_t4(0,8,tail) 与原版 rsh() 逐位相同", o_orig==o_t4)
chk("门1：与 Cora 先导 Python 版逐位相同", o_orig==o_py)
chk("B1 几何均值 = 0.7044（审核环境值）", abs(gm(o_orig)-0.7044)<5e-5)
chk("门2：确定性", o2==run_t4(0.25,8,0)[0])
oi,li,mv=run_t4(0.0,8,1)
chk("E1：α=0 时局部孤立行 64、全部移动", li==64 and mv==64)
chk("E1：结果仍是合法置换", sorted(oi)==list(range(n)))
print("总判定：", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
