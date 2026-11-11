import argparse,ctypes as C,hashlib,json,time,traceback
from pathlib import Path
import numpy as np
from native import BASE,Matrix,Rect,I,L,ip,lp
from resource_slots import acquire
ap=argparse.ArgumentParser();ap.add_argument('--matrix');ap.add_argument('--method');ap.add_argument('--W',type=int,default=16);ap.add_argument('--seed',type=int,default=0);args=ap.parse_args();token=acquire();start=time.time();out=BASE/'work/stage3-generated';out.mkdir(exist_ok=True);key=f'{args.matrix}__{args.method}__W{args.W}__seed{args.seed}';r=dict(matrix=args.matrix,method=args.method,W=args.W,seed=args.seed,start=start,status='INCOMPLETE')
try:
 m=Matrix(args.matrix);ne=np.flatnonzero(m.deg).tolist();em=np.flatnonzero(m.deg==0).tolist()
 if args.method=='B0':pi=list(range(m.n));rule='identity baseline, original numbering retained'
 elif args.method=='B-RCM-ref':
  lib=C.CDLL(str(BASE/'work/liblarge-rcm.dylib'));lib.large_rcm.argtypes=[C.c_int,L,I,I];pi=np.empty(m.n,np.int32);lib.large_rcm(m.n,lp(m.p),ip(m.c),ip(pi));pi=pi.tolist();rule='deterministic degree/ID RCM on nonempty vertices; empty vertices appended ascending'
 else:
  method='rsh-α0' if args.method=='B1' else args.method;g=Rect(m,ne)
  try:pi=g.order(method,args.W,args.seed)+em
  finally:g.close()
  rule='new T23 computation searches nonempty A0 vertices only, appends empty original IDs ascending (T20 common convention); frozen T21 indexed reuse remains unchanged'
 assert sorted(pi)==list(range(m.n));p=out/(key+'.order.json');p.write_text(json.dumps(pi,separators=(',',':'))+'\n');r.update(status='OK',path=str(p),runtime_path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,empty_rule=rule)
except Exception as e:r.update(error=str(e),traceback=traceback.format_exc())
r.update(end=time.time());r['seconds']=r['end']-start;(out/(key+'.record.json')).write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
