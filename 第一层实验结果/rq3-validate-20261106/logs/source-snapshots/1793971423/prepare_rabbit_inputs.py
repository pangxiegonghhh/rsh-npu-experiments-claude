import ctypes as C,json,hashlib,time
from native import BASE,Matrix,L,I,lp,ip
lib=C.CDLL(str(BASE/'work/librabbit-edges.dylib'));lib.rabbit_edges.argtypes=[C.c_int,L,I,C.c_int,C.c_char_p];records=[]
for matrix in ['cora','ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1']:
 m=Matrix(matrix)
 for mode in ['B','U']:
  p=BASE/'work/linux-transfer'/(matrix+'-'+mode+'.edges.gz');start=time.time();rc=lib.rabbit_edges(m.n,lp(m.p),ip(m.c),int(mode=='B'),str(p).encode());assert rc==0;h=hashlib.sha256()
  with p.open('rb') as f:
   for b in iter(lambda:f.read(2**20),b''):h.update(b)
  r=dict(matrix=matrix,mode=mode,n_original=m.n,entries=int(m.p[-1]) if mode=='B' else int(m.p[-1])//2,sha256=h.hexdigest(),size=p.stat().st_size,path=str(p),seconds=time.time()-start,rule='each stored A0 coordinate once on original row/column bipartite vertices' if mode=='B' else 'each undirected A0 edge once (r<c); demo symmetrizes');records.append(r);print(matrix,mode,r['size'],flush=True)
(BASE/'logs/rabbit-inputs.json').write_text(json.dumps(records,indent=2))
