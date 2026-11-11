import argparse,hashlib,json,os,sys,time,traceback,resource
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix
import pynndescent
from native import BASE,Matrix
def execute(matrix,variant,seed,use_native=False):
 m=Matrix(matrix);ne=np.flatnonzero(m.deg).astype(np.int32);n=len(ne);a=csr_matrix((np.ones(len(m.c),np.float32),m.c,m.p),shape=(m.n,m.n))[ne];a.sort_indices();k=min(16,n-1)
 if n<=17:
  x=(a@a.T).toarray();deg=np.asarray(a.getnnz(axis=1));dist=deg[:,None]+deg[None,:]-2*x if variant=='H' else 1-x/(deg[:,None]+deg[None,:]-x);neighbors=np.asarray([sorted((j for j in range(n) if j!=i),key=lambda j:(dist[i,j],j))[:k] for i in range(n)])
 else:
  index=pynndescent.NNDescent(a,n_neighbors=k+1,metric='jaccard' if variant=='J' else 'hamming',random_state=seed,n_jobs=1,low_memory=True,verbose=True)
  nn,_=index.neighbor_graph;neighbors=np.asarray([[int(j) for j in row if j!=i and j>=0][:k] for i,row in enumerate(nn)])
  if neighbors.shape!=(n,k):raise RuntimeError('NNDescent failed to provide 16 nonself neighbors')
 if use_native:return finish_native(a,neighbors,ne,m,variant,n,k)
 edgekeys=set()
 for i,row in enumerate(neighbors):
  for j in row:edgekeys.add((min(i,int(j)),max(i,int(j))))
 def intersection(i,j):
  return np.intersect1d(a.indices[a.indptr[i]:a.indptr[i+1]],a.indices[a.indptr[j]:a.indptr[j+1]],assume_unique=True).size
 deg=np.diff(a.indptr);edges=[];graphdeg=np.zeros(n,np.int32)
 for i,j in edgekeys:
  inter=intersection(i,j);distance=int(deg[i]+deg[j]-2*inter) if variant=='H' else 1-inter/(int(deg[i]+deg[j])-inter)
  edges.append((distance,i,j));graphdeg[i]+=1;graphdeg[j]+=1
 edges.sort();parent=list(range(n));size=[1]*n
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 tree=[[] for _ in range(n)]
 for d,i,j in edges:
  x,y=find(i),find(j)
  if x==y:continue
  if size[x]<size[y]:x,y=y,x
  parent[y]=x;size[x]+=size[y];tree[i].append((d,j));tree[j].append((d,i))
 comps={}
 for i in range(n):comps.setdefault(find(i),[]).append(i)
 order=[]
 for comp in sorted(comps.values(),key=lambda c:(-len(c),int(ne[c[0]]))):
  root=min(comp,key=lambda i:(-int(graphdeg[i]),int(ne[i])));stack=[(root,-1)]
  while stack:
   i,prev=stack.pop();order.append(int(ne[i]));stack.extend((j,i) for _,j in sorted(tree[i],key=lambda p:(p[0],int(ne[p[1]])),reverse=True) if j!=prev)
 order.extend(map(int,np.flatnonzero(m.deg==0)));assert sorted(order)==list(range(m.n))
 rng=np.random.default_rng(0);sample=np.sort(rng.choice(n,size=min(128,n),replace=False));recalls=[]
 for i in sample:
  inter=(a[int(i)]@a.T).toarray().ravel();d=deg+deg[i]-2*inter if variant=='H' else 1-inter/(deg+deg[i]-inter);d[i]=np.inf;exact=np.lexsort((np.arange(n),d))[:k];recalls.append(len(set(exact)&set(neighbors[i]))/k if k else 1.)
 return order,dict(graph_components=len(comps),graph_edges=len(edges),zero_distance_edges=sum(d==0 for d,_,_ in edges),recall_sample_original_rows=[int(ne[i]) for i in sample],recall_at16=float(np.mean(recalls)),graph_type='nonempty row exact-distance undirected union of approximate neighbors; Kruskal MSF',pynndescent_version=pynndescent.__version__,n_jobs=1,metric_units='symmetric difference count' if variant=='H' else 'Jaccard distance')
def finish_native(a,neighbors,ne,m,variant,n,k):
 from c1_forest import order as forest
 permutation,diag=forest(a,neighbors,variant);pi=[int(ne[i]) for i in permutation]+list(map(int,np.flatnonzero(m.deg==0)));assert sorted(pi)==list(range(m.n));rng=np.random.default_rng(0);sample=np.sort(rng.choice(n,size=min(128,n),replace=False));recalls=[];deg=np.diff(a.indptr)
 for i in sample:
  inter=(a[int(i)]@a.T).toarray().ravel();d=deg+deg[i]-2*inter if variant=='H' else 1-inter/(deg+deg[i]-inter);d[i]=np.inf;exact=np.lexsort((np.arange(n),d))[:k];recalls.append(len(set(exact)&set(neighbors[i]))/k if k else 1.)
 diag.update(recall_sample_original_rows=[int(ne[i]) for i in sample],recall_at16=float(np.mean(recalls)),graph_type='unchanged PyNNDescent neighbors; exact-distance undirected union/Kruskal/DFS native storage port',pynndescent_version=pynndescent.__version__,n_jobs=1,metric_units='symmetric difference count' if variant=='H' else 'Jaccard distance',forest_backend='validated C++ contiguous arrays; same distances, tie rules and traversal')
 return pi,diag
if __name__=='__main__':
 from resource_slots import acquire
 cpu_slot=acquire()
 ap=argparse.ArgumentParser();ap.add_argument('--matrix');ap.add_argument('--variant');ap.add_argument('--seed',type=int,default=0);args=ap.parse_args();key=f'{args.matrix}__C1-{args.variant}__W16__seed{args.seed}';out=BASE/'work/external';out.mkdir(exist_ok=True);r=dict(matrix=args.matrix,method='C1-'+args.variant,W=16,seed=args.seed,start=time.time(),status='INCOMPLETE',command=sys.argv)
 try:
  native=args.matrix in ['reddit','ogbn-products']
  if native:assert json.loads((BASE/'logs/c1-native-forest-gate.json').read_text())['passed']
  pi,diag=execute(args.matrix,args.variant,args.seed,use_native=native);p=out/(key+'.order.json');p.write_text(json.dumps(pi,separators=(',',':'))+'\n');r.update(status='OK',path=str(p),runtime_path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,diagnostics=diag)
 except Exception as e:r.update(error=str(e),traceback=traceback.format_exc())
 r.update(end=time.time());r['seconds']=r['end']-r['start'];r['peak_mem_mb']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20;(out/(key+'.record.json')).write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
