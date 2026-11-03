"""Prepare E0 integrated guard cases without reordering or changing routing."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.e0_prepare import make_case
from rsh.planner import Matrix, execute_cpu
from rsh.prepare import export


def prepare(root: Path) -> None:
    root.mkdir(parents=True,exist_ok=True)
    for k in (16,32,48):
        for n in (16,17,32,33,64):make_case(root,16,k,n)
    make_case(root,30,70,40)
    m,n,gk=32,33,181
    ac=np.zeros((m,gk),dtype=np.float16)
    maps=[np.arange(17)*3+1,np.arange(37)*4+2]
    for r in range(m):
        cols=maps[r//16]
        ac[r,cols]=((r*11+np.arange(len(cols))*7)%17-8)/8
    counts=np.count_nonzero(ac,axis=1);ptr=np.zeros(m+1,dtype=np.int32);ptr[1:]=np.cumsum(counts)
    rr,cc=np.nonzero(ac);a=Matrix(ptr,cc.astype(np.int32),ac[rr,cc],(m,gk))
    b=np.fromfunction(lambda r,c:((r*13+c*5)%19-9)/8,(gk,n)).astype(np.float16)
    tiles=[];refs=[];gp=[0]
    for group,cols in enumerate(maps):
        for start in range(0,len(cols),16):
            sub=cols[start:start+16];tile=np.zeros((16,16),dtype=np.float16);tile[:,:len(sub)]=ac[group*16:(group+1)*16,sub]
            ref=np.full(16,gk,dtype=np.int32);ref[:len(sub)]=sub;tiles.append(tile);refs.append(ref)
        gp.append(len(tiles))
    plan={'variant':'V1','cube_ptr':np.array(gp,dtype=np.int64),'colref':np.array(refs,dtype=np.int32).reshape(-1),'tiles':np.array(tiles,dtype=np.float16),'rowmap':np.arange(m,dtype=np.int32),'srows':np.empty(0,dtype=np.int32),'valid':np.ones(m,dtype=np.uint8)}
    # Golden is independent of the packed tile layout.
    golden=(ac.astype(np.float64)@b.astype(np.float64)).astype(np.float32)
    output=execute_cpu(a,plan,b);assert np.array_equal(output,golden)
    export(a,plan,b,golden,root/'ADJACENT_U17_U37_N33'/'V1',{'experiment':'E0-S4','window_widths':[17,37]})

if __name__=='__main__':prepare(Path(sys.argv[1]))
