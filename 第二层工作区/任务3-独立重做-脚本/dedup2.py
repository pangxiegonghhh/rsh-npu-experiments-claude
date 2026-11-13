# H2 稳健性：窗口执行顺序被打乱（按密度降序）/ 多核切分后，AIV 取数重复率还剩多少
import importlib.util, sys
W=16; ALPHA=1/295.0; BETA=1/505.0
spec=importlib.util.spec_from_file_location('pilot',sys.argv[1]); pilot=importlib.util.module_from_spec(spec); sys.modules['pilot']=pilot; spec.loader.exec_module(pilot)
hdr=None
for line in open(sys.argv[2]):
    if line.startswith('%'): continue
    p=line.split()
    if hdr is None: hdr=1; n=int(p[0]); ent=[set() for _ in range(n)]; continue
    r,c=int(p[0])-1,int(p[1])-1
    if r!=c: ent[r].add(c); ent[c].add(r)
M=pilot.SparseMatrix(n_rows=n,n_cols=n,entries=[[(c,1.0) for c in sorted(e)] for e in ent])
order,_,_,_=pilot.rsh_reorder(M,k=8,weighted_alpha=0.0)
def rate(seqs,L):
    hit=tot=0
    for seq in seqs:
        last={}
        for t,cc in enumerate(seq):
            tot+=1
            if cc in last and t-last[cc]<L: hit+=1
            else: last[cc]=t
    return hit/tot
for name,o in (('B0',list(range(n))),('B1',order)):
    pos={old:i for i,old in enumerate(o)}; rows=[sorted(pos[c] for c in ent[old]) for old in o]
    wins=[rows[s:s+W] for s in range(0,n,W)]; c=[len(set().union(*map(set,w))) for w in wins]; z=[sum(map(len,w)) for w in wins]
    idx=sorted(range(len(wins)),key=lambda i:-z[i]/c[i]); best=None; C=0; Z=sum(z)
    for k in range(len(idx)+1):
        ms=max(ALPHA*C,BETA*Z)
        if best is None or ms<best[0]: best=(ms,k)
        if k<len(idx): C+=c[idx[k]]; Z-=z[idx[k]]
    aiv_density=idx[best[1]:]            # 按密度降序的 AIV 窗口
    aiv_seq=sorted(aiv_density)          # 按行号
    flat=lambda ws:[cc for i in ws for r in wins[i] for cc in r]
    def chunks(ws,ncore):                # 每核领一段连续窗口，各有自己的环形缓冲
        k=(len(ws)+ncore-1)//ncore; return [flat(ws[i:i+k]) for i in range(0,len(ws),k)]
    within=[[cc for r in wins[i] for cc in r] for i in aiv_seq]   # 只算同一窗口内的重复（下界，与窗口顺序无关）
    for L in (32,64):
        print(name,f'L={L}','行号序单流 %.1f%%'%(100*rate([flat(aiv_seq)],L)),'| 密度序单流 %.1f%%'%(100*rate([flat(aiv_density)],L)),
              '| 行号序40核 %.1f%%'%(100*rate(chunks(aiv_seq,40),L)),'| 密度序40核 %.1f%%'%(100*rate(chunks(aiv_density,40),L)),'| 仅窗口内 %.1f%%'%(100*rate(within,L)))
