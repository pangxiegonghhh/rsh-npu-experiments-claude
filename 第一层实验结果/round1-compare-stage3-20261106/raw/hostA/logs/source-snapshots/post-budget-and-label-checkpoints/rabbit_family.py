import argparse,ctypes as C,hashlib,json,time,traceback,sys
from pathlib import Path
import numpy as np
from native import BASE,Matrix,I,L,ip,lp
from shared_phase_budget import start_budget
LIB=C.CDLL(str(BASE/'work/librabbit-local.dylib'));LIB.rabbit_local.argtypes=[C.c_int,L,I,I,C.c_int,C.c_int,C.c_int,I]
def coarse_order(m,record):
 mapping=np.loadtxt(record['runtime_path'],dtype=np.int64);assert sorted(mapping.tolist())==list(range(len(mapping)));ne=np.flatnonzero(m.deg);assert len(mapping)>int(ne.max());order=sorted(map(int,ne),key=lambda r:int(mapping[r]));return order
def local(m,coarse,W=16,cn=False):
 arr=np.asarray(coarse,np.int32);out=np.empty(m.n,np.int32);LIB.rabbit_local(m.n,lp(m.p),ip(m.c),ip(arr),len(arr),W,int(cn),ip(out));assert np.array_equal(np.sort(out),np.arange(m.n));return out.tolist()
if __name__=='__main__':
 from resource_slots import acquire
 cpu_slot=acquire()
 ap=argparse.ArgumentParser();ap.add_argument('--matrix');ap.add_argument('--mode',choices=['B','U']);ap.add_argument('--rep',type=int,default=0);ap.add_argument('--W',type=int,default=16);ap.add_argument('--cn',action='store_true');args=ap.parse_args();name=('C5' if args.mode=='B' else 'C5-U')+('-CN' if args.cn else '');key=f'{args.matrix}__{name}__W{args.W}__seed{args.rep}';out=BASE/'work/external';out.mkdir(exist_ok=True);start=time.time();record=dict(matrix=args.matrix,method=name,W=args.W,seed=args.rep,start=start,status='INCOMPLETE',command=sys.argv)
 timer=None
 try:
  assert json.loads((BASE/'logs/rabbit-reproducibility-gate.json').read_text())['passed'];assert json.loads((BASE/'logs/rabbit-local-gate.json').read_text())['passed'];m=Matrix(args.matrix);parent=json.loads((BASE/'work/rabbit-coarse'/f'{args.matrix}-{args.mode}-repeat{args.rep}.record.json').read_text());assert parent['status']=='OK';timer=start_budget(parent['coarse_seconds'],start,out/key);coarse=coarse_order(m,parent);tm=time.time();pi=local(m,coarse,args.W,args.cn);sec=time.time()-tm;p=out/(key+'.order.json');p.write_text(json.dumps(pi,separators=(',',':'))+'\n');record.update(status='OK',path=str(p),runtime_path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,local_seconds=sec,coarse_seconds=parent['coarse_seconds'],diagnostics=dict(author_ref=parent['author_ref'],coarse_mapping_sha256=parent['mapping_sha256'],coarse_vertices=len(coarse),seed_api_unavailable=True,requested_seed_label=args.rep,actual_seed=None,threads=1,local_rule='current-row common-neighbor chain' if args.cn else 'anchor exact Jaccard grouping',Q=8*args.W,parent_record=str(BASE/'work/rabbit-coarse'/f'{args.matrix}-{args.mode}-repeat{args.rep}.record.json')))
 except Exception as e:record.update(error=str(e),traceback=traceback.format_exc())
 if timer is not None:timer.cancel()
 record['end']=time.time();record['seconds']=record.get('coarse_seconds',0)+record.get('local_seconds',0);(out/(key+'.record.json')).write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
