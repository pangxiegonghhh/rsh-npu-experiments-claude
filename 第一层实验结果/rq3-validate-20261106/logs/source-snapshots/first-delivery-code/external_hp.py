import argparse,ctypes as C,hashlib,json,sys,time,traceback,resource
from pathlib import Path
import numpy as np
import scipy.sparse as sp
import kahypar
from native import BASE,Matrix
from capacity import repair
from resource_slots import acquire
ap=argparse.ArgumentParser();ap.add_argument('--matrix');ap.add_argument('--W',type=int,default=16);ap.add_argument('--rep',type=int,default=0);args=ap.parse_args();token=acquire();key=f'{args.matrix}__C6-HP__W{args.W}__seed0'+(f'__repeat{args.rep}' if args.rep else '');out=BASE/'work/stage3-generated';out.mkdir(exist_ok=True);record=dict(matrix=args.matrix,method='C6-HP',W=args.W,seed=0,repeat=args.rep,start=time.time(),status='INCOMPLETE',params='column-net unit nets and vertices; direct k-way km1; epsilon=.03 seed0; exact capacity repair',command=sys.argv)
try:
 m=Matrix(args.matrix);ne=np.flatnonzero(m.deg);k=(len(ne)+args.W-1)//args.W;workspace=int(m.p[-1])*56+m.n*128
 record['workspace_preflight_bytes']=workspace
 if workspace>8*2**30:raise RuntimeError(f'HP representation preflight {workspace} bytes exceeds frozen8GiB workspace budget')
 if k<=1:pi=ne.tolist()+np.flatnonzero(m.deg==0).tolist();diag=dict(solver='trivial at most one nonempty group',k=k)
 else:
  idx=np.full(m.n,-1,np.int32);idx[ne]=np.arange(len(ne),dtype=np.int32);a=sp.csr_matrix((np.ones(len(m.c),np.int8),m.c.copy(),m.p.copy()),shape=(m.n,m.n));a.sort_indices();a=a[ne];p=a.indptr.astype(np.int64);c=idx[a.indices];h=hashlib.sha256();h.update(p.tobytes());h.update(c.tobytes());config=BASE/'deps/kahypar-km1-kway-v1.3.7.ini';record.update(k=int(k),nonempty_nodes=len(ne),nonempty_column_nets=len(ne),pins=len(c),hypergraph_sha256=h.hexdigest(),canonical_net_and_pin_order='original columns ascending; each net pins ascending original nonempty-row ID',kahypar_version=kahypar.__version__,configuration_sha256=hashlib.sha256(config.read_bytes()).hexdigest());phase=out/(key+'.phase.json');phase.write_text(json.dumps(dict(record,phase='constructing hypergraph',time=time.time()),indent=2));hg=kahypar.Hypergraph(len(ne),len(ne),p.tolist(),c.tolist(),k);context=kahypar.Context();context.loadINIconfiguration(str(config));context.setK(k);context.setEpsilon(.03);context.setSeed(0);context.suppressOutput(True);phase.write_text(json.dumps(dict(record,phase='partitioning',time=time.time()),indent=2));tm=time.time();kahypar.partition(hg,context);partition_sec=time.time()-tm;labels=np.full(m.n,-1,np.int32);labels[ne]=[int(hg.blockID(v)) for v in range(len(ne))];objective=int(kahypar.connectivityMinusOne(hg));phase.write_text(json.dumps(dict(record,phase='exact capacity repair',partition_sec=partition_sec,pre_km1=objective,time=time.time()),indent=2));pi,diag=repair(m,labels,args.W);assert diag['pre_objective_sumU']-len(ne)==objective;diag.update(partition_seconds=partition_sec,pre_km1=objective,post_km1=diag['post_objective_sumU']-len(ne),epsilon=.03,k=k,unit_hyperedge_weights=True,unit_vertex_weights=True)
 assert sorted(pi)==list(range(m.n));p=out/(key+'.order.json');p.write_text(json.dumps(pi,separators=(',',':'))+'\n');record.update(status='OK',path=str(p),runtime_path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),size=p.stat().st_size,diagnostics=diag)
except Exception as e:record.update(error=str(e),traceback=traceback.format_exc())
record.update(end=time.time());record['seconds']=record['end']-record['start'];record['peak_mem_mb']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20;(out/(key+'.record.json')).write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k not in ['diagnostics','traceback']}),flush=True)
