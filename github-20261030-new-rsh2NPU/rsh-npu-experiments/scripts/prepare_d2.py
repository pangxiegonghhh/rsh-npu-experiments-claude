"""D2 CPU-exact layouts and host-only allocation randomization; kernels frozen."""
from __future__ import annotations
import hashlib,json,platform,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d2';sys.path.insert(0,str(ROOT))
from scripts.prepare_d1 import KEYS,read,sha,save
from scripts.hv_cases import check_split
from rsh.planner import Matrix,partition,layout,execute_cpu
DEV=['SNAP_ca-HepTh','SNAP_email-Enron','HB_bcsstk17']
ALL=sorted(p.stem for p in (ROOT/'inputs').glob('*.npz'))
EVAL=[m for m in ALL if m not in DEV]
ARGS=['t4/H-V','t4/H-V','t8/H-V','t8/H-V','V0','V2']
LABELS=['T4-A','T4-B','T8-A','T8-B','V0','V2']
PROFILE_ARGS=ARGS+['t4/G-only/V2','t4/ST-only/V0','t8/G-only/V2','t8/ST-only/V0']
PROFILE_LABELS=LABELS+['T4-G','T4-ST','T8-G','T8-ST']
LAYOUT_KEYS=['cube_ptr','colref','tiles','rowmap','srows']

def immutable(p:Path,data:bytes)->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==data,str(p)
    else:p.write_bytes(data)

def link(src:Path,dst:Path)->None:
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists():assert sha(dst)==sha(src)
    else:dst.symlink_to(src.resolve())

def export_case(base:Path,dst:Path,data:dict,layout_dir:Path,metadata:dict)->None:
    cfg=list(map(int,(base/'config.txt').read_text().split()));m,k,n,stride,nnz=cfg[:5]
    arrays={q:np.ascontiguousarray(data[q]).tobytes() for q in LAYOUT_KEYS}
    for q,b in arrays.items():immutable(layout_dir/(q+'.bin'),b)
    if not np.all(data['valid']):immutable(layout_dir/'valid.bin',np.ascontiguousarray(data['valid']).tobytes())
    for q in KEYS:
        src=layout_dir/(q+'.bin') if q in LAYOUT_KEYS or (q=='valid' and not np.all(data['valid'])) else base/(q+'.bin')
        link(src,dst/(q+'.bin'))
    immutable(dst/'native_clear.flag',b'AIV_zero_v1\n')
    groups=len(data['cube_ptr'])-1;blocks=len(data['tiles']);srows=len(data['srows'])
    immutable(dst/'config.txt',(' '.join(map(str,[m,k,n,stride,nnz,groups,blocks,srows]))+'\n').encode())
    meta=metadata|{'m':m,'k':k,'n':n,'stride':stride,'nnz':nnz,'groups':groups,'blocks':blocks,'aiv_rows':srows,'valid_rows':int(data['valid'].sum()),'full_output':bool(np.all(data['valid'])),'empty_valid_scope':not bool(np.any(data['valid'])),'files_sha256':{q:sha(dst/(q+'.bin')) for q in KEYS}}
    immutable(dst/'metadata.json',(json.dumps(meta,indent=2)+'\n').encode())

def control(base:Path,dst:Path)->None:
    for name in ['config.txt','metadata.json']+[q+'.bin' for q in KEYS]:link(base/name,dst/name)
    immutable(dst/'native_clear.flag',b'AIV_zero_v1\n')

def branch_plans(plan:dict,m:int)->tuple[dict,dict]:
    valid=np.zeros(m,np.uint8);rows=plan['rowmap'];valid[rows[rows>=0]]=1
    g=plan|{'srows':np.empty(0,np.int32),'valid':valid}
    sv=np.zeros(m,np.uint8);sv[plan['srows']]=1
    st={'cube_ptr':np.zeros(1,np.int64),'colref':np.empty(0,np.int32),'tiles':np.empty((0,16,16),np.float16),'rowmap':np.empty(0,np.int32),'srows':plan['srows'],'valid':sv}
    assert not np.any(valid&sv);return g,st

def prepare_matrix(name:str,widths:list[int],a:Matrix,order:np.ndarray,base_roots:dict[int,Path],provenance:dict,small:bool=False)->dict:
    timing={'matrix':name,'machine':platform.machine(),'hostname':platform.node(),'fixed_order':True,'reorder_remeasured':False,'thresholds':{}}
    for tag,tn,ti in [('t4',4,2),('t8',8,4)]:
        routes=[];route=None
        for repeat in range(3):
            t=time.perf_counter();s=partition(a,order,tn,ti,16);routes.append(time.perf_counter()-t);check_split(a,s)
            if route is not None:assert route==s
            route=s
        root=D/'plans'/tag/name;root.mkdir(parents=True,exist_ok=True)
        routing=provenance|{'matrix':name,'tau_nnz':tn,'tau_inc':ti,'split':route}
        immutable(root/'routing.json',(json.dumps(routing,indent=2)+'\n').encode())
        formats=[];plan=None
        for repeat in range(3):
            t=time.perf_counter();p=layout(a,order,route,'H-V');formats.append(time.perf_counter()-t)
            if plan is not None:
                for q in LAYOUT_KEYS+['valid']:assert np.array_equal(plan[q],p[q])
            plan=p
        if not small:
            historical=ROOT/'results/hv/plans'/name/'routing.json' if tag=='t4' else ROOT/'results/hv/grid/plans/t8_4'/name/'routing.json'
            if historical.exists():assert read(historical)['split']==route
            reference=ROOT/'cases_hv'/name/'N64/H-V' if tag=='t4' else ROOT/'cases_hv_grid/t8_4'/name/'N64/H-V'
            if reference.exists():
                for q in LAYOUT_KEYS:assert hashlib.sha256(plan[q].tobytes()).hexdigest()==sha(reference/(q+'.bin')),(tag,name,q)
        g,st=branch_plans(plan,a.shape[0]);nnz=np.diff(a.ptr);assert np.all((g['valid']|st['valid'])[nnz>0])
        stats={}
        for label,rows in [('G',[r for grp in route['groups'] for r in grp]),('S',route['residual']),('T',route['tail']),('Z',route['zeros'])]:stats[label]={'rows':len(rows),'nnz':int(nnz[rows].sum()) if rows else 0}
        stats|={'groups':len(route['groups']),'k16_tiles':len(plan['tiles']),'cube_slots':int(plan['tiles'].size),'plan_bytes':sum(plan[q].nbytes for q in LAYOUT_KEYS+['valid'])}
        immutable(root/'structure.json',(json.dumps(stats,indent=2)+'\n').encode())
        t=time.perf_counter()
        for n in widths:
            base=base_roots[n];target=ROOT/'cases_d2'/name/f'N{n}'
            export_case(base,target/tag/'H-V',plan,root/'full',provenance|{'thresholds':[tn,ti],'kind':'D2_full_HV','routing_sha256':sha(root/'routing.json')})
            export_case(base,target/tag/'G-only/V2',g,root/'G',provenance|{'thresholds':[tn,ti],'kind':'D2_frozen_G_only','routing_sha256':sha(root/'routing.json')})
            export_case(base,target/tag/'ST-only/V0',st,root/'ST',provenance|{'thresholds':[tn,ti],'kind':'D2_frozen_ST_only','routing_sha256':sha(root/'routing.json')})
            for v in ['V0','V2']:
                source=base.parent/v if small else ROOT/('cases_'+v.lower())/name/f'N{n}'/v
                control(source,target/v)
            if small:
                cfg=list(map(int,(base/'config.txt').read_text().split()));b=np.fromfile(base/'rhs.bin',np.float16).reshape(a.shape[1]+1,cfg[3])[:a.shape[1],:n];gold=np.fromfile(base/'golden.bin',np.float32).reshape(a.shape[0],cfg[3])[:,:n]
                for p in [plan,g,st]:
                    mask=p['valid'].astype(bool);np.testing.assert_allclose(execute_cpu(a,p,b)[mask],gold[mask],atol=1e-3,rtol=1e-3)
        timing['thresholds'][tag]={'partition_seconds':routes,'layout_seconds':formats,'export_seconds':time.perf_counter()-t,'structure':stats}
    return timing

def prepare(scope:str)->dict:
    names=DEV if scope=='dev' else EVAL;records=[];roots=[]
    for name in names:
        src=ROOT/'inputs'/(name+'.npz');t=time.perf_counter();a=Matrix.load(str(src));load=time.perf_counter()-t;od=ROOT/'results/v2/orders'/name;original=read(od/'structure.json');assert sha(src)==original['input_sha256'] and sha(od/'order.bin')==original['order_sha256']
        t=time.perf_counter();order=np.fromfile(od/'order.bin',np.int32);order_load=time.perf_counter()-t;assert np.array_equal(np.sort(order),np.arange(a.shape[0]))
        widths=[64] if scope=='dev' else [16,64,256]
        rec=prepare_matrix(name,widths,a,order,{n:ROOT/'cases_v0'/name/f'N{n}'/'V0' for n in widths},{'input_sha256':sha(src),'order_sha256':sha(od/'order.bin'),'order_source':str(od.relative_to(ROOT))})
        rec|={'input_load_seconds':load,'order_load_seconds':order_load,'historical_common_reorder_seconds':original['seconds']};records.append(rec);roots.extend(str((ROOT/'cases_d2'/name/f'N{n}').relative_to(ROOT)) for n in widths);print('D2_CPU',scope,name,flush=True)
    if scope=='dev':
        for c in read(ROOT/'results/d1/smoke_cases.json')['cases']:
            source=ROOT/'cases_d1'/('smoke_'+c['name'])/f'N{c["n"]}';base=source/'V0';cfg=list(map(int,(base/'config.txt').read_text().split()));a=Matrix(np.fromfile(base/'ptr.bin',np.int32),np.fromfile(base/'cols.bin',np.int32),np.fromfile(base/'values.bin',np.float16),(cfg[0],cfg[1]));order=np.array(read(base/'metadata.json')['order'],np.int32)
            records.append(prepare_matrix('smoke_'+c['name'],[c['n']],a,order,{c['n']:base},{'kind':'D2_threshold_smoke','order':order.tolist()},True));roots.append(f'cases_d2/smoke_{c["name"]}/N{c["n"]}')
    manifest={'scope':scope,'roots':roots,'files':{}}
    for root in roots:
        for arg in sorted(set(PROFILE_ARGS)):
            for p in (ROOT/root/arg).iterdir():
                if p.is_file():manifest['files'][str(p.relative_to(ROOT))]=sha(p)
    immutable(D/(scope+'_case_manifest.json'),(json.dumps(manifest,indent=2)+'\n').encode())
    save(D/(scope+'_preparation_'+platform.machine()+'.json'),{'scope':scope,'records':records,'timing_scope':'CPU fixed order partition/layout/export only; no fresh ordering, H2D or GPU execution; three repeated CPU route/layout computations','roots':roots})
    return manifest

def generate()->list[Path]:
    paths=[]
    for kind in ['runner','profile_runner']:
        src=ROOT/'diagnostics/d1b'/(kind+'.cpp');s=src.read_text();needle='  std::vector<std::unique_ptr<Case>>cases;\n  for(int i=7;i<argc;++i)cases.push_back(std::make_unique<Case>(root/argv[i],cores));';assert s.count(needle)==1
        replacement='''  std::vector<std::unique_ptr<Case>>cases(argc-7);
  uint32_t allocationSeed=uint32_t(std::stoul(argv[5]))^0x5A17B39Du;
  std::mt19937 allocationRng(allocationSeed);
  std::vector<size_t>allocationOrder(cases.size());std::iota(allocationOrder.begin(),allocationOrder.end(),0);
  std::shuffle(allocationOrder.begin(),allocationOrder.end(),allocationRng);
  for(auto j:allocationOrder){cases[j]=std::make_unique<Case>(root/argv[7+j],cores);if(!cases[j]->nativeClear)throw std::runtime_error("D2 requires native clear for every record");}
'''
        s=s.replace(needle,replacement)
        pos=s.index('  f<<"],\\\"host_trace_schema')
        s=s[:pos]+'''  f<<"],\\\"allocation_seed\\\":"<<allocationSeed<<",\\\"allocation_order\\\":[";
  for(size_t i=0;i<allocationOrder.size();++i){if(i)f<<',';f<<allocationOrder[i];}
'''+s[pos:]
        # Device call and validation bodies are identical to D1b; only constructor ordering/output metadata differ.
        for start,end in [(' void call(', ' void validate(' if kind=='runner' else ' void collectEvents'),(' void validate(', '\n};')]:
            old=src.read_text();assert old[old.index(start):old.index(end,old.index(start))]==s[s.index(start):s.index(end,s.index(start))]
        target=ROOT/'diagnostics/d2'/(kind+'.cpp');immutable(target,s.encode());paths.append(target)
    return paths

def build()->None:
    parent=read(ROOT/'results/d1b/build.json');selected=read(ROOT/'results/d1b/backend_selection.json');assert parent['new_zero_library_sha256']==selected['zero_library_sha256'];base=ROOT/'build_v4';dest=ROOT/'build_d2';dest.mkdir(exist_ok=True);programs={};commands={}
    for label,source in zip(['formal','profile'],generate()):
        c=parent['commands'][label]['compile'].copy();obj=dest/(label+'.o');exe=dest/('rsh_runner_d2_'+label);c[c.index('-c')+1]=str(source);c[c.index('-o')+1]=str(obj);link=parent['commands'][label]['link'].copy();link=[str(obj) if v.endswith('/'+label+'.o') else v for v in link];link[link.index('-o')+1]=str(exe)
        for phase,cmd in [('compile',c),('link',link)]:
            x=subprocess.run(cmd,cwd=base,capture_output=True,text=True,timeout=180);(D/f'build_{label}_{phase}.log').write_text(x.stdout+x.stderr);assert x.returncode==0,x.stderr
        programs[label]={'path':str(exe.relative_to(ROOT)),'sha256':sha(exe)};commands[label]={'compile':c,'link':link};q=D/'device_binary'/exe.name;q.parent.mkdir(exist_ok=True);shutil.copy2(exe,q)
    index=read(ROOT/'results/d1b/build_objects/index.json');saved={}
    for name,e in index.items():
        assert sha(ROOT/name)==e['sha256'];q=D/'build_objects'/Path(e['saved']).name;q.parent.mkdir(exist_ok=True);shutil.copy2(ROOT/name,q);saved[name]={'saved':str(q.relative_to(ROOT)),'sha256':e['sha256']}
    save(D/'build_objects/index.json',saved);save(D/'build.json',{'programs':programs,'commands':commands,'kernel_recompiled':False,'spmm_and_zero_objects_sha256':{k:v['sha256'] for k,v in index.items()},'parent_backend_selection_sha256':sha(ROOT/'results/d1b/backend_selection.json'),'constructor_change':'random allocation order independent from logical record indices and timed call order; recorded seed/order','timed_device_calls_unchanged':True})
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=['dev','eval']);p.add_argument('--build',action='store_true');p.add_argument('--generate-only',action='store_true');a=p.parse_args();D.mkdir(exist_ok=True)
    if a.generate_only:generate()
    if a.scope:prepare(a.scope)
    if a.build:build()
