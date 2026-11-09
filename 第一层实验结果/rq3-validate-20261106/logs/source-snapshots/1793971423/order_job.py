import argparse,json,hashlib,sys,time,traceback,ctypes as C
from pathlib import Path
import numpy as np
from native import BASE,Matrix,Rect,I,L,ip,lp
from evaluate_t23 import read_order
from ls_runtime import local_search
def induced_order(m,K,method):
 if method=='SlashBurn' and len(K)==m.n:
  lib=C.CDLL(str(BASE/'work/libslashburn.dylib'));lib.rq_slashburn.argtypes=[C.c_int,L,I,C.c_int,I,I];out=np.empty(m.n,np.int32);sizes=np.empty(2,np.int32);lib.rq_slashburn(m.n,lp(m.p),ip(m.c),max(1,int(.005*m.n)),ip(out),ip(sizes));front,tail=map(int,sizes);return out[:front].tolist()+sorted(set(out[front:front+tail].tolist()),key=lambda v:-m.deg[v])+out[front+tail:].tolist()
 K=sorted(K);idx=np.full(m.n,-1,np.int32);idx[K]=np.arange(len(K),dtype=np.int32);a=[set(int(idx[u]) for u in m.c[m.p[v]:m.p[v+1]] if idx[u]>=0) for v in K]
 if method=='B-RCM-ref':
  deg=[len(x) for x in a];key=lambda v:(deg[v],v);seen=[False]*len(K);out=[]
  for s in sorted(range(len(K)),key=key):
   if seen[s]:continue
   seen[s]=True;q=[s];j=0
   while j<len(q):
    v=q[j];j+=1
    for u in sorted(a[v],key=key):
     if not seen[u]:seen[u]=True;q.append(u)
   out+=q
  return [K[v] for v in out[::-1]]
 lib=C.CDLL(str(BASE/'work/libslashburn.dylib'));lib.rq_slashburn.argtypes=[C.c_int,L,I,C.c_int,I,I];ptr=np.asarray([0]+list(np.cumsum([len(x) for x in a])),np.int64);cols=np.fromiter((v for row in a for v in row),dtype=np.int32,count=int(ptr[-1]));out=np.empty(len(K),np.int32);sizes=np.empty(2,np.int32);lib.rq_slashburn(len(K),lp(ptr),ip(cols),max(1,int(.005*len(K))),ip(out),ip(sizes));front,tail=map(int,sizes);gcc=out[front:front+tail].tolist();result=out[:front].tolist()+sorted(set(gcc),key=lambda v:-len(a[v]))+out[front+tail:].tolist();return [K[v] for v in result]
def run(r):
 m=Matrix(r['matrix']);pi=read_order(r['runtime_path']);kind=r['kind'];tau=r.get('tau');method=r['member'];W=int(r.get('W',16));diag={}
 if kind in ['ls','lsfull']:
  if len(pi)!=m.n:
   assert r.get('start_source')=='rerun';original=read_order(r['original_runtime_path']);pi=pi+[v for v in original if m.deg[v]<=tau]
  return local_search(m,pi,W,None if kind=='lsfull' else tau,r.get('lambda',0),int(r.get('seed') or 0),r.get('checkpoint_path'))
 K=[v for v in range(m.n) if tau is None or m.deg[v]>tau]
 if method=='B0':order=[v for v in pi if tau is None or m.deg[v]>tau]
 elif method in ['B-RCM-ref','SlashBurn']:order=induced_order(m,K,method)
 else:
  g=Rect(m,K)
  try:order=g.order(method,W,int(r.get('seed') or 0))
  finally:g.close()
 assert sorted(order)==K
 if tau is None and kind=='rerun':assert order==pi,'K=all differs from original order'
 return order,diag
if __name__=='__main__':
 from resource_slots import acquire
 cpu_slot=acquire()
 ap=argparse.ArgumentParser();ap.add_argument('record');ap.add_argument('--output-dir');args=ap.parse_args();r=json.loads(Path(args.record).read_text());out=Path(args.output_dir) if args.output_dir else BASE/'work/order-jobs';out.mkdir(exist_ok=True);key=Path(args.record).stem;record=dict(r,start=time.time(),status='INCOMPLETE',command=sys.argv)
 try:
  r['checkpoint_path']=str(out/(key+'.checkpoint.json'));record['checkpoint_path']=r['checkpoint_path']
  pi,diag=run(r);p=out/(key+'.order.json');p.write_text(json.dumps(dict(matrix=r['matrix'],member=r['member'],row_perm=pi,kind=r['kind'],tau=r.get('tau'),W=r.get('W',16),diagnostics=diag),separators=(',',':'))+'\n');record.update(status='OK',path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,diagnostics=diag)
 except Exception as e:record.update(error=str(e),traceback=traceback.format_exc())
 record.update(end=time.time());record['seconds']=record['end']-record['start'];(out/(key+'.record.json')).write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='diagnostics'}),flush=True)
