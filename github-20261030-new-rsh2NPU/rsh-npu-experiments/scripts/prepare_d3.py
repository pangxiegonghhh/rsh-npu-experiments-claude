"""D3 frozen L/F/J workflows, common zero exclusion and AIV tail; CPU preparation."""
from __future__ import annotations
import argparse,hashlib,json,platform,shutil,sys,time
from pathlib import Path
import numpy as np
from scipy.sparse import csr_matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));D=ROOT/'results/d3'
from rsh.planner import Matrix,reorder,partition,layout,execute_cpu
from rsh.prepare import export
from scripts.prepare_d2 import immutable,export_case,branch_plans,sha,read,save,LAYOUT_KEYS,ALL
from scripts.prepare_d1 import transform,KEYS
from scripts.hv_cases import check_split
ARGS=['L/H-V','L/H-V','F/H-V','F/H-V','J/H-V','J/H-V','O/H-V','J0/H-V','V2-Z/V2']
LABELS=['L-A','L-B','F-A','F-B','J-A','J-B','O','J0','V2-Z']
PROFILE_ARGS=ARGS+[f'{v}/{b}/{kind}' for v in ['L','F','J'] for b,kind in [('G-only','V2'),('ST-only','V0')]]
PROFILE_LABELS=LABELS+[f'{v}-{b}' for v in ['L','F','J'] for b in ['G','ST']]
POINTS=[(m,n) for m in ALL for n in [16,64,256]]

def subset(a:Matrix,rows:np.ndarray)->Matrix:
    x=csr_matrix((a.val.astype(np.float32),a.col,a.ptr),shape=a.shape)[rows].tocsr()
    return Matrix(x.indptr.astype(np.int32),x.indices.astype(np.int32),x.data.astype(np.float16),(len(rows),a.shape[1]))

def restricted_order(a:Matrix)->tuple[np.ndarray,dict]:
    t=time.perf_counter();length=np.diff(a.ptr);eligible=np.flatnonzero(length>8).astype(np.int32);selected=time.perf_counter()-t;t=time.perf_counter();sub=subset(a,eligible);sliced=time.perf_counter()-t;t=time.perf_counter()
    if len(eligible):local,stats=reorder(sub,256,16,True);order=eligible[local]
    else:order=np.empty(0,np.int32);stats={'empty_candidate_domain':True}
    return order,dict(select_seconds=selected,subset_seconds=sliced,reorder_seconds=time.perf_counter()-t,reorder_stats=stats,eligible_rows=len(eligible),eligible_nnz=len(sub.col),domain='ascending original row IDs with nnz>8, original full K column space, local row IDs in candidate sampling')

def split_fixed(a:Matrix,order:np.ndarray)->dict:
    length=np.diff(a.ptr);z=np.flatnonzero(length==0).tolist();s=np.flatnonzero((length>0)&(length<=8)).tolist();seq=[int(r) for r in order if length[r]>8];r=len(seq)//16*16
    return dict(groups=[seq[i:i+16] for i in range(0,r,16)],residual=s,tail=seq[r:],zeros=z,tau_nnz=8,tau_inc=4,w=16)

def splits(a:Matrix,global_order:np.ndarray,local_order:np.ndarray)->dict:
    length=np.diff(a.ptr);nz=global_order[length[global_order]>0];j=partition(a,nz,8,4,16);j['zeros']=np.flatnonzero(length==0).tolist();o=partition(a,nz,0,0,16);o['zeros']=j['zeros'].copy();o['tau_nnz']=8;o['tau_inc']=4
    out={'L':split_fixed(a,local_order),'F':split_fixed(a,global_order),'J':j,'O':o,'J0':partition(a,global_order,8,4,16)}
    for v,s in out.items():
        check_split(a,s)
        if v!='J0':assert all(length[r]>0 for g in s['groups'] for r in g) and all(length[r]>0 for r in s['residual']+s['tail'])
    assert out['L']['residual']==out['F']['residual'];assert len(out['L']['tail'])==len(out['F']['tail']);assert out['L']['zeros']==out['F']['zeros']==out['J']['zeros']==out['O']['zeros']
    return out

def stats(a:Matrix,route:dict,plan:dict)->dict:
    length=np.diff(a.ptr);out={}
    for k,rs in [('G',[r for g in route['groups'] for r in g]),('S',route['residual']),('T',route['tail']),('Z',route['zeros'])]:out[k]=dict(rows=len(rs),nnz=int(length[rs].sum()) if rs else 0,zero_rows=int((length[rs]==0).sum()) if rs else 0)
    out.update(groups=len(route['groups']),k16_tiles=len(plan['tiles']),cube_slots=plan['tiles'].size,plan_bytes=sum(plan[k].nbytes for k in LAYOUT_KEYS+['valid']),tail_nnz_fraction=out['T']['nnz']/max(1,len(a.col)))
    out['cube_slots']=int(out['cube_slots']);return out

def one(name:str,a:Matrix,gorder:np.ndarray,widths:list[int],bases:dict[int,Path],prov:dict,retime:bool,small:bool=False)->dict:
    od=D/'orders'/name;od.mkdir(parents=True,exist_ok=True);immutable(od/'F_order.bin',gorder.tobytes());lp=od/'L_order.bin';timing=dict(matrix=name,machine=platform.machine(),hostname=platform.node(),common_input_load_excluded=True)
    if not lp.exists():
        lo,t=restricted_order(a);immutable(lp,lo.tobytes());save(od/('L_creation_'+platform.machine()+'.json'),t)
    lo=np.fromfile(lp,np.int32);eligible=np.flatnonzero(np.diff(a.ptr)>8);assert np.array_equal(np.sort(lo),eligible)
    if retime:
        t=time.perf_counter();fresh,full_stats=reorder(a,256,16,True);timing['global_reorder_seconds']=time.perf_counter()-t;timing['global_reorder_stats']=full_stats;timing['global_exact_saved_order']=np.array_equal(fresh,gorder)
        freshlocal,localtime=restricted_order(a);timing['L']=localtime;timing['L_exact_frozen_order']=np.array_equal(freshlocal,lo);save(od/('reproduction_'+platform.machine()+'.json'),timing)
        assert timing['global_exact_saved_order'] and timing['L_exact_frozen_order'],('ordering reproduction differs',name)
    else:timing['L_creation_reused']=read(od/('L_creation_'+platform.machine()+'.json')) if (od/('L_creation_'+platform.machine()+'.json')).exists() else None
    t=time.perf_counter();routes=splits(a,gorder,lo);timing['all_routes_seconds']=time.perf_counter()-t;timing['paths']={}
    for v,route in routes.items():
        pd=D/'plans'/v/name;immutable(pd/'routing.json',(json.dumps(prov|{'variant':v,'split':route},indent=2)+'\n').encode());t=time.perf_counter();p=layout(a,gorder,route,'H-V');format_s=time.perf_counter()-t;st=stats(a,route,p);immutable(pd/'structure.json',(json.dumps(st,indent=2)+'\n').encode())
        if v=='J0' and not small:
            assert read(ROOT/'results/d2/plans/t8'/name/'routing.json')['split']==route
            for key in LAYOUT_KEYS:assert sha(ROOT/'results/d2/plans/t8'/name/'full'/(key+'.bin'))==hashlib.sha256(p[key].tobytes()).hexdigest()
        g,sv=branch_plans(p,a.shape[0]);t=time.perf_counter()
        for n in widths:
            base=bases[n];target=ROOT/'cases_d3'/name/f'N{n}';meta=prov|dict(workflow=v,routing_sha256=sha(pd/'routing.json'),L_order_sha256=sha(lp),F_order_sha256=sha(od/'F_order.bin'),zero_policy='global_zero_rows_excluded' if v!='J0' else 'historical_D2_head_zero',tail_policy='AIV',thresholds=[8,4])
            export_case(base,target/v/'H-V',p,pd/'full',meta)
            if v in ['L','F','J']:
                export_case(base,target/v/'G-only/V2',g,pd/'G',meta|{'scope':'G owned rows'})
                export_case(base,target/v/'ST-only/V0',sv,pd/'ST',meta|{'scope':'S+T owned rows'})
            if small:
                cfg=list(map(int,(base/'config.txt').read_text().split()));b=np.fromfile(base/'rhs.bin',np.float16).reshape(a.shape[1]+1,cfg[3])[:a.shape[1],:n];gold=np.fromfile(base/'golden.bin',np.float32).reshape(a.shape[0],cfg[3])[:,:n]
                for q in [p,g,sv]:
                    mask=q['valid'].astype(bool);np.testing.assert_allclose(execute_cpu(a,q,b)[mask],gold[mask],atol=1e-3,rtol=1e-3)
        timing['paths'][v]=dict(layout_seconds=format_s,export_seconds=time.perf_counter()-t,structure=st)
    for n in widths:
        source=bases[n].parent/'V2' if small else ROOT/'cases_v2'/name/f'N{n}'/'V2';dst=ROOT/'cases_d3'/name/f'N{n}'/'V2-Z/V2';transform(source,dst,'Z');immutable(dst/'native_clear.flag',b'AIV_zero_v1\n')
    return timing

def capture_v2z()->None:
    for root in sorted((ROOT/'cases_d3').glob('*/N*')):
        matrix=root.parent.name;case=root/'V2-Z/V2';pd=D/'plans/V2-Z'/matrix/'full'
        for key in LAYOUT_KEYS+['valid']:immutable(pd/(key+'.bin'),(case/(key+'.bin')).read_bytes())

def prepare(retime:bool=False,restore_only:bool=False)->dict:
    import scipy
    save(D/('environment_'+platform.machine()+'.json'),dict(python=sys.version,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform()))
    if restore_only:
        for name in ALL:assert (D/'orders'/name/'L_order.bin').exists(),('restore requires frozen order',name)
    records=[];roots=[]
    for name in ALL:
        src=ROOT/'inputs'/(name+'.npz');t=time.perf_counter();a=Matrix.load(str(src));loaded=time.perf_counter()-t;od=ROOT/'results/v2/orders'/name;md=read(od/'structure.json');assert sha(src)==md['input_sha256'] and sha(od/'order.bin')==md['order_sha256'];go=np.fromfile(od/'order.bin',np.int32)
        rec=one(name,a,go,[16,64,256],{n:ROOT/'cases_v0'/name/f'N{n}'/'V0' for n in [16,64,256]},dict(matrix=name,input_sha256=sha(src),global_order_source=str(od.relative_to(ROOT)),global_order_sha256=md['order_sha256']),retime)
        rec['input_load_seconds']=loaded;rec['historical_global_reorder_seconds']=md['seconds'];records.append(rec);roots.extend(f'cases_d3/{name}/N{n}' for n in [16,64,256]);save(D/('preparation_progress_'+platform.machine()+'.json'),dict(completed_matrices=[r['matrix'] for r in records],retime=retime));print('D3_CPU',name,flush=True)
    for c in read(ROOT/'results/d1/smoke_cases.json')['cases']:
        base=ROOT/c['root']/'V0';cfg=list(map(int,(base/'config.txt').read_text().split()));a=Matrix(np.fromfile(base/'ptr.bin',np.int32),np.fromfile(base/'cols.bin',np.int32),np.fromfile(base/'values.bin',np.float16),(cfg[0],cfg[1]));go=np.array(read(base/'metadata.json')['order'],np.int32);name='smoke_'+c['name'];records.append(one(name,a,go,[c['n']],{c['n']:base},dict(matrix=name,smoke=True,global_order=go.tolist()),False,True));roots.append(f'cases_d3/{name}/N{c["n"]}')
    name='smoke_mixed97';source=ROOT/'cases_d3_smoke_source'/name/'N33';base=source/'V0'
    if not base.exists():
        rng=np.random.default_rng(20261030);dense=np.zeros((97,97),np.float16)
        for r in range(97):
            if r%11==0:continue
            cols=np.arange(12)+(r%3)*16 if r%4==0 else np.arange(5)+(r%4)*16;dense[r,cols]=rng.uniform(-1,1,len(cols)).astype(np.float16)
        cs=csr_matrix(dense.astype(np.float32));a=Matrix(cs.indptr.astype(np.int32),cs.indices.astype(np.int32),cs.data.astype(np.float16),cs.shape);go,_=reorder(a,256,16,True);b=rng.uniform(-1,1,(97,33)).astype(np.float16);gold=(dense.astype(np.float64)@b.astype(np.float64)).astype(np.float32);split=partition(a,go,8,4,16)
        for v in ['V0','V2']:export(a,layout(a,go,split,v),b,gold,source/v,dict(kind='D3_mixed_smoke',order=go.tolist()))
    cfg=list(map(int,(base/'config.txt').read_text().split()));a=Matrix(np.fromfile(base/'ptr.bin',np.int32),np.fromfile(base/'cols.bin',np.int32),np.fromfile(base/'values.bin',np.float16),(cfg[0],cfg[1]));go=np.array(read(base/'metadata.json')['order'],np.int32);records.append(one(name,a,go,[33],{33:base},dict(matrix=name,smoke=True,global_order=go.tolist()),False,True));roots.append(f'cases_d3/{name}/N33')
    mixed_routes={v:read(D/'plans'/v/name/'routing.json')['split'] for v in ['L','F','J']}
    assert all(s['groups'] and (s['residual'] or s['tail']) for s in mixed_routes.values())
    manifest=dict(roots=roots,files={})
    for root in roots:
        for arg in sorted(set(PROFILE_ARGS)):
            for p in sorted((ROOT/root/arg).iterdir()):
                if p.is_file():manifest['files'][str(p.relative_to(ROOT))]=sha(p)
    capture_v2z()
    immutable(D/'case_manifest.json',(json.dumps(manifest,indent=2)+'\n').encode());save(D/('preparation_'+platform.machine()+'.json'),dict(records=records,retime=retime,scope='CPU reorder/domain selection, routes/layout/export; no application E2E',roots=roots));return manifest
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--capture-only',action='store_true');a.add_argument('--retime',action='store_true');a.add_argument('--restore-only',action='store_true');x=a.parse_args();capture_v2z() if x.capture_only else prepare(x.retime,x.restore_only)
