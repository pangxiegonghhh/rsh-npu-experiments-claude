import argparse,json,time,hashlib,traceback,sys,resource
import numpy as np
import pymetis
from native import BASE,Matrix
from capacity import repair
from resource_slots import acquire
cpu_slot=acquire()
ap=argparse.ArgumentParser();ap.add_argument('--matrix');ap.add_argument('--W',type=int,default=16);args=ap.parse_args();r=dict(matrix=args.matrix,method='C8-METIS',W=args.W,seed=0,start=time.time(),status='INCOMPLETE',params='edgecut; ufactor=30; seed=0; direct k-way; exact capacity repair',command=sys.argv)
out=BASE/'work/external';out.mkdir(exist_ok=True);key=f'{args.matrix}__C8-METIS__W{args.W}__seed0'
try:
 assert json.loads((BASE/'logs/capacity-repair-gate.json').read_text())['passed'];m=Matrix(args.matrix);ne=np.flatnonzero(m.deg);idx=np.full(m.n,-1,np.int64);idx[ne]=np.arange(len(ne));ptr=np.asarray([0]+list(np.cumsum(m.deg[ne])),np.int64);cols=idx[m.c];k=(len(ne)+args.W-1)//args.W;part=pymetis.part_graph(k,adjacency=pymetis.CSRAdjacency(ptr,cols),recursive=False,options=pymetis.Options(seed=0,ufactor=30));labels=np.full(m.n,-1,np.int32);labels[ne]=part.vertex_part;pi,diag=repair(m,labels,args.W);diag.update(edge_cuts=int(part.edge_cuts),pymetis_version=pymetis.version,options=dict(seed=0,ufactor=30,recursive=False));p=out/(key+'.order.json');p.write_text(json.dumps(pi,separators=(',',':'))+'\n');r.update(status='OK',path=str(p),runtime_path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,diagnostics=diag)
except Exception as e:r.update(error=str(e),traceback=traceback.format_exc())
r.update(end=time.time());r['seconds']=r['end']-r['start'];r['peak_mem_mb']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20;(out/(key+'.record.json')).write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='diagnostics'}),flush=True)
