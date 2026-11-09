import ctypes as C,hashlib,json,time
from native import BASE,Matrix,L,I,lp,ip
from resource_slots import acquire
token=acquire();lib=C.CDLL(str(BASE/'work/librabbit-edges.dylib'));lib.rabbit_edges.argtypes=[C.c_int,L,I,C.c_int,C.c_char_p];records=[]
for matrix in ['reddit','ogbn-products']:
 m=Matrix(matrix)
 for mode in ['B','U']:
  p=BASE/'work/linux-transfer'/(matrix+'-'+mode+'.edges.gz');begin=time.time()
  assert not p.exists(),'keep an existing prepared input'
  assert lib.rabbit_edges(m.n,lp(m.p),ip(m.c),int(mode=='B'),str(p).encode())==0
  h=hashlib.sha256()
  with p.open('rb') as f:
   for data in iter(lambda:f.read(2**20),b''):h.update(data)
  r=dict(matrix=matrix,mode=mode,path=str(p),sha256=h.hexdigest(),size=p.stat().st_size,seconds=time.time()-begin,entries=int(m.p[-1]) if mode=='B' else int(m.p[-1])//2,rule='A0 bipartite graph; original row vertex and n+column vertex' if mode=='B' else 'A0 undirected edges r<c, author demo symmetrizes');records.append(r);print(matrix,mode,r['size'],flush=True)
(BASE/'logs/rabbit-second-inputs.json').write_text(json.dumps(records,indent=2))
