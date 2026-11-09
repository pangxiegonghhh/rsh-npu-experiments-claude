import hashlib,json,time
from pathlib import Path
import numpy as np
import pymetis,pynndescent
from resource_slots import acquire
from native import BASE,Matrix
from capacity import repair
from external_c1 import execute
from evaluate_t23 import read_order
token=acquire();checks=[]
pi,diag=execute('cora','H',0);path=BASE/'work/external/cora__C1-H__W16__seed0.order.json';assert pi==read_order(path);checks.append(dict(candidate='C1-H',same_seed=0,identical=True,version=pynndescent.__version__,n_jobs=1,reference_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
m=Matrix('cora');ne=np.flatnonzero(m.deg);idx=np.full(m.n,-1,np.int64);idx[ne]=np.arange(len(ne));ptr=np.asarray([0]+list(np.cumsum(m.deg[ne])),np.int64);cols=idx[m.c];k=(len(ne)+15)//16;part=pymetis.part_graph(k,adjacency=pymetis.CSRAdjacency(ptr,cols),recursive=False,options=pymetis.Options(seed=0,ufactor=30));labels=np.full(m.n,-1,np.int32);labels[ne]=part.vertex_part;pi,diag=repair(m,labels,16);path=BASE/'work/external/cora__C8-METIS__W16__seed0.order.json';assert pi==read_order(path);checks.append(dict(candidate='C8-METIS',same_seed=0,identical=True,pymetis_version=pymetis.version,seed=0,ufactor=30,reference_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(BASE/'logs/external-repeated-cora-gate.json').write_text(json.dumps(dict(passed=True,checks=checks,C1_J_gate=str(BASE/'logs/c1-reproducibility.json'),Rabbit_gate=str(BASE/'logs/rabbit-reproducibility-gate.json')),indent=2));print('EXTERNAL_REPEATED_CORA_IDENTICAL')
