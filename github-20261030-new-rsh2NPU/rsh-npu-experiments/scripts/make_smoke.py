from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from rsh.planner import Matrix,partition,layout,execute_cpu
from rsh.prepare import export,VARIANTS
from scipy.sparse import csr_matrix

root=Path(__file__).resolve().parents[1]
for m in (7,16,17,32,65):
    rng=np.random.default_rng(1000+m)
    dense=np.zeros((m,37),np.float16)
    for r in range(m):
        js=[0] if r%5==0 else [0,1,2,3,4]
        dense[r,js]=rng.uniform(-1,1,len(js)).astype(np.float16)
    if m>16:dense[15]=0
    csr=csr_matrix(dense.astype(np.float32))
    a=Matrix(csr.indptr.astype(np.int32),csr.indices.astype(np.int32),csr.data.astype(np.float16),csr.shape)
    order=np.arange(m,dtype=np.int32)
    split=partition(a,order)
    for n in (33,64):
        b=rng.uniform(-1,1,(37,n)).astype(np.float16)
        golden=(dense.astype(np.float64)@b.astype(np.float64)).astype(np.float32)
        for variant in VARIANTS:
            plan=layout(a,order,split,variant)
            actual=execute_cpu(a,plan,b)
            keep=plan['valid'].astype(bool)
            np.testing.assert_allclose(actual[keep],golden[keep],atol=1e-3,rtol=1e-3)
            export(a,plan,b,golden,root/'cases'/f'smoke_M{m}'/f'N{n}'/variant,
                   {'kind':'synthetic_correctness','order':'identity','split':split})
print('Prepared 80 synthetic case layouts; full/retained CPU correctness passed.')
