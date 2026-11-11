import argparse,hashlib,json,time,traceback
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from native import BASE,Matrix,Candidates
from rabbit_family import coarse_order
from shared_phase_budget import start_budget
from resource_slots import acquire
ap=argparse.ArgumentParser();ap.add_argument('--matrix');ap.add_argument('--method');ap.add_argument('--W',type=int,default=16);ap.add_argument('--seed',type=int,default=0);args=ap.parse_args();token=acquire();start=time.time();out=BASE/'work/stage3-generated';out.mkdir(exist_ok=True);key=f'{args.matrix}__{args.method}__W{args.W}__seed{args.seed}';record=dict(matrix=args.matrix,method=args.method,W=args.W,seed=args.seed,start=start,status='INCOMPLETE')
timer=None
try:
 m=Matrix(args.matrix);name=args.method;parent=None
 if name.endswith('-R'):
  base=name[:-2];p=BASE/'work/rabbit-coarse'/f'{m.name}-U-repeat{args.seed}.record.json';parent=json.loads(p.read_text());assert parent['status']=='OK';timer=start_budget(parent['coarse_seconds'],start,out/key);coarse=coarse_order(m,parent);O=np.asarray(coarse+np.flatnonzero(m.deg==0).tolist(),np.int32);inverse=np.empty(m.n,np.int32);inverse[O]=np.arange(m.n,dtype=np.int32);ptr=np.zeros(m.n+1,np.int64);ptr[1:]=np.cumsum(m.deg[O]);cols=np.empty(len(m.c),np.int32)
  for i,v in enumerate(O):cols[ptr[i]:ptr[i+1]]=inverse[m.c[m.p[v]:m.p[v+1]]]
  renamed=SimpleNamespace(n=m.n,p=ptr,c=cols);g=Candidates(renamed);perm,diag=g.order(base,args.W,args.seed);g.close();pi=O[np.asarray(perm)].tolist();diag.update(coarse_mapping_sha256=parent['mapping_sha256'],coarse_source=str(p),symmetric_row_and_column_renumbering=True,Rabbit_seed_api_unavailable=True,actual_Rabbit_seed=None)
 else:
  assert name in ['C3-A','C3-W4-noP'];g=Candidates(m);pi,diag=g.order(name,args.W,args.seed);g.close()
 assert sorted(pi)==list(range(m.n));p=out/(key+'.order.json');p.write_text(json.dumps(pi,separators=(',',':'))+'\n');local=time.time()-start;record.update(status='OK',path=str(p),runtime_path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,diagnostics=diag,local_seconds=local,coarse_seconds=parent['coarse_seconds'] if parent else 0,seconds=local+(parent['coarse_seconds'] if parent else 0))
 if name in ['C3-A','C3-A-R'] and m.n<50000:record['alias_of']='C3-W4-R' if name.endswith('-R') else 'C3-W4';record['alias_nonindependent']=True
except Exception as e:record.update(error=str(e),traceback=traceback.format_exc(),seconds=time.time()-start)
if timer is not None:timer.cancel()
record['end']=time.time();(out/(key+'.record.json')).write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
