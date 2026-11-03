"""Prepare H-V only; freeze reusable G/S/T and use saved V2 permutations."""
from pathlib import Path
import hashlib,json,os,sys,time
import numpy as np
from scipy.sparse import csr_matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rsh.planner import Matrix,reorder,partition,layout,execute_cpu
from rsh.prepare import export

def digest(p: Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p: Path,x: dict)->None:
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix('.tmp');t.write_text(json.dumps(x,indent=2));t.replace(p)
def check_split(a: Matrix,split: dict)->None:
    rows=[r for g in split['groups'] for r in g]+split['residual']+split['tail']+split['zeros']
    assert sorted(rows)==list(range(a.shape[0])) and len(set(rows))==len(rows)
    assert all(len(g)==16 for g in split['groups']) and len(split['tail'])<16

def smoke_cases(dest: Path)->list[dict]:
    cases=[]
    for m in [7,16,17,32,65]:
        rng=np.random.default_rng(31000+m);dense=np.zeros((m,37),np.float16)
        for r in range(m):
            js=[0] if r%7==0 else [0,1,2,3,4]
            dense[r,js]=rng.uniform(-1,1,len(js)).astype(np.float16)
        if m>16:dense[15]=0;dense[m//2]=rng.uniform(-1,1,37).astype(np.float16)
        a0=csr_matrix(dense.astype(np.float32));a=Matrix(a0.indptr.astype(np.int32),a0.indices.astype(np.int32),a0.data.astype(np.float16),a0.shape)
        order,_=reorder(a,256,16,True);split=partition(a,order,4,2,16);check_split(a,split)
        plan=layout(a,order,split,'H-V')
        for n in [33,64]:
            b=rng.uniform(-1,1,(37,n)).astype(np.float16);gold=(dense.astype(np.float64)@b.astype(np.float64)).astype(np.float32)
            np.testing.assert_allclose(execute_cpu(a,plan,b),gold,atol=1e-3,rtol=1e-3)
            target=ROOT/'cases_hv'/f'smoke_M{m}'/f'N{n}'/'H-V';export(a,plan,b,gold,target,{'kind':'reordered_mixed_smoke','order':order.tolist(),'split':split})
            cases.append({'name':f'M{m}_N{n}','root':str(target.parent.relative_to(ROOT)),'m':m,'n':n,'cube_groups':len(split['groups']),'srows':len(plan['srows']),'tail':len(split['tail']),'order_nonidentity':not np.array_equal(order,np.arange(m))})
    # An explicit divisible-M case exercises residual-induced 15-row tail + Cube.
    for kind in ['dynamic_tail','all_zero','disjoint']:
        m=32 if kind=='dynamic_tail' else 17;k=37;rng=np.random.default_rng(41000+m);dense=np.zeros((m,k),np.float16)
        if kind=='dynamic_tail':
            dense[:,:5]=rng.uniform(-1,1,(m,5)).astype(np.float16);dense[0,1:]=0
        elif kind=='disjoint':
            dense[np.arange(m),np.arange(m)]=rng.uniform(.5,1,m).astype(np.float16)
        c=csr_matrix(dense.astype(np.float32));a=Matrix(c.indptr.astype(np.int32),c.indices.astype(np.int32),c.data.astype(np.float16),c.shape)
        order=np.arange(m,dtype=np.int32)[::-1].copy()
        if kind=='dynamic_tail':order=np.roll(order,1)
        split=partition(a,order,4,2,16);check_split(a,split);plan=layout(a,order,split,'H-V')
        if kind=='dynamic_tail':assert len(split['groups'])==1 and len(split['residual'])==1 and len(split['tail'])==15
        n=33;b=rng.uniform(-1,1,(k,n)).astype(np.float16);gold=(dense.astype(np.float64)@b.astype(np.float64)).astype(np.float32)
        np.testing.assert_allclose(execute_cpu(a,plan,b),gold,atol=1e-3,rtol=1e-3)
        target=ROOT/'cases_hv'/f'smoke_{kind}'/f'N{n}'/'H-V';export(a,plan,b,gold,target,{'kind':kind,'order':order.tolist(),'split':split})
        cases.append({'name':kind,'root':str(target.parent.relative_to(ROOT)),'m':m,'n':n,'cube_groups':len(split['groups']),'srows':len(plan['srows']),'tail':len(split['tail']),'order_nonidentity':True})
    assert any(c['cube_groups'] and c['srows'] for c in cases)
    save(dest/'smoke_preparation.json',{'passed':True,'cases':cases});return cases

def prepare_real(source: Path,dest: Path,tau_nnz: int=4,tau_inc: int=2)->dict:
    a=Matrix.load(str(source));od=ROOT/'results/v2/orders'/source.stem;old=json.loads((od/'structure.json').read_text())
    assert digest(source)==old['input_sha256'] and digest(od/'order.bin')==old['order_sha256']
    order=np.fromfile(od/'order.bin',np.int32);assert np.array_equal(np.sort(order),np.arange(a.shape[0]))
    started=time.perf_counter();split=partition(a,order,tau_nnz,tau_inc,16);part_seconds=time.perf_counter()-started;check_split(a,split)
    pd=dest/'plans'/source.stem;pd.mkdir(parents=True,exist_ok=True)
    routing={'matrix':source.stem,'input_sha256':digest(source),'order_sha256':old['order_sha256'],'split':split}
    if (pd/'routing.json').exists():assert json.loads((pd/'routing.json').read_text())==routing
    else:save(pd/'routing.json',routing)
    t=time.perf_counter();plan=layout(a,order,split,'H-V');layout_seconds=time.perf_counter()-t
    nnz=np.diff(a.ptr);grows=[r for g in split['groups'] for r in g]
    def stats(rows: list[int])->dict:return {'rows':len(rows),'nnz':int(nnz[rows].sum()) if rows else 0,'zero_rows':int(np.sum(nnz[rows]==0)) if rows else 0}
    unions=[int(np.sum(plan['colref'][plan['cube_ptr'][i]*16:plan['cube_ptr'][i+1]*16]!=a.shape[1])) for i in range(len(split['groups']))]
    v2=json.loads((ROOT/'cases_v2'/source.stem/'N16/V2/metadata.json').read_text())
    summary={'matrix':source.stem,'m':a.shape[0],'k':a.shape[1],'nnz':len(a.col),'order_sha256':old['order_sha256'],'routing_sha256':digest(pd/'routing.json'),'tau_nnz':tau_nnz,'tau_inc':tau_inc,'w':16,'G':stats(grows),'S':stats(split['residual']),'T':stats(split['tail']),'Z':stats(split['zeros']),'cube_groups':len(split['groups']),'k16_tiles':len(plan['tiles']),'v2_k16_tiles':v2['k16_tiles'],'partition_seconds':part_seconds,'layout_seconds':layout_seconds,'reused_v2_order_seconds':old['seconds'],'column_union_quantiles':np.quantile(unions,[0,.25,.5,.75,1]).tolist() if unions else [0]*5,'cube_nnz':stats(grows)['nnz'],'aiv_rows':len(plan['srows']),'cube_physical_slots':len(plan['tiles'])*256,'b_gather_rows_per_call':len(plan['colref']),'plan_bytes':sum(plan[k].nbytes for k in ['cube_ptr','colref','tiles','rowmap','srows','valid'])}
    if not(pd/'structure.json').exists():save(pd/'structure.json',summary)
    for n in [16,64,256]:
        base=ROOT/'cases_v0'/source.stem/f'N{n}/V0';stride=(n+15)//16*16;target=ROOT/'cases_hv'/source.stem/f'N{n}/H-V'
        if not(target/'metadata.json').exists():
            b=np.fromfile(base/'rhs.bin',np.float16).reshape(a.shape[1]+1,stride)[:a.shape[1],:n]
            golden=np.fromfile(base/'golden.bin',np.float32).reshape(a.shape[0],stride)[:,:n]
            export(a,plan,b,golden,target,summary|{'n':n,'b_seed':20261017+n,'tail_policy':'AIV','full_output':True})
        meta=json.loads((target/'metadata.json').read_text())
        for key,h in meta['files_sha256'].items():assert digest(target/f'{key}.bin')==h
        for v in ['V0','V2']:
            control=ROOT/f'cases_{v.lower()}'/source.stem/f'N{n}'/v;cm=json.loads((control/'metadata.json').read_text())
            for key in ['ptr','cols','values','rhs','golden']:assert meta['files_sha256'][key]==cm['files_sha256'][key]
            link=target.parent/v
            if not link.exists():link.symlink_to(os.path.relpath(control,link.parent),target_is_directory=True)
    print('HV_PREPARED',source.stem,'G',summary['G'],'S',summary['S'],'T',summary['T'],flush=True);return summary
