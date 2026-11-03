"""V2 only: bounded RSH-style locality ordering, fixed W16 all Cube.
V0/V1 are current-device controls. Stop before H-V; checkpoint every process.
"""
from pathlib import Path
import hashlib,json,os,random,statistics,subprocess,sys,time,traceback
import numpy as np
from scipy.sparse import csr_matrix
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsh.planner import Matrix,reorder,layout,execute_cpu
from rsh.prepare import export

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    p.parent.mkdir(parents=True,exist_ok=True)
    q=p.with_suffix('.tmp');q.write_text(json.dumps(x,indent=2));q.replace(p)

def smoke_cases(dest):
    report=[]
    for m in [7,16,17,32,65]:
        rng=np.random.default_rng(21000+m);dense=np.zeros((m,37),np.float16)
        for r in range(m):
            js=[(r%3)*9+j for j in range(1+(r%5))]
            dense[r,js]=rng.uniform(-1,1,len(js)).astype(np.float16)
        dense[m//2]=0
        if m>16:dense[1]=0;dense[-1]=0;dense[3,36]=.75
        csr=csr_matrix(dense.astype(np.float32));a=Matrix(csr.indptr.astype(np.int32),csr.indices.astype(np.int32),csr.data.astype(np.float16),csr.shape)
        order,stats=reorder(a,256,16,True)
        assert not np.array_equal(order,np.arange(m)), 'Smoke must exercise nonidentity scatter'
        plan=layout(a,order,{'w':16,'tail':[]},'V2')
        for n in [33,64]:
            b=rng.uniform(-1,1,(37,n)).astype(np.float16)
            golden=(dense.astype(np.float64)@b.astype(np.float64)).astype(np.float32)
            np.testing.assert_allclose(execute_cpu(a,plan,b),golden,atol=1e-3,rtol=1e-3)
            export(a,plan,b,golden,ROOT/'cases_v2'/f'smoke_M{m}'/f'N{n}'/'V2',{'kind':'synthetic_reordered','order':order.tolist(),'reorder':stats})
        report.append({'m':m,'order':order.tolist(),'cpu_correct':True,'zero_rows':np.flatnonzero(np.diff(a.ptr)==0).tolist(),'tail_rows':m%16})
    save(dest/'smoke_preparation.json',{'passed':True,'cases':report})

def main():
    dest=ROOT/'results/v2';dest.mkdir(exist_ok=True);exe=ROOT/'build_v4/rsh_runner'
    files=sorted((ROOT/'inputs').glob('*.npz'));assert len(files)==8
    sources=list((ROOT/'npu').glob('*'))+[ROOT/'rsh/planner.py',ROOT/'rsh/prepare.py']
    manifest={'version':'V2','source_hashes':{str(p.relative_to(ROOT)):digest(p) for p in sorted(sources) if p.is_file()},'controller_sha256':digest(Path(__file__)),'executable_sha256':digest(exe),'inputs':{p.name:digest(p) for p in files},'protocol':{'new_main_version':'V2','controls':['V0','V1'],'primary_ratio':'V1/V2','secondary_ratio':'V0/V2','estimator':'median within-iteration ratios, then median of three process medians','w':16,'tail':'zero padded Cube','order':'bounded shared-column weighted-Jaccard kNN, minimum spanning forest DFS, segment two-opt','candidate_budget':256,'k':16,'refine':True,'approximate_search':True,'aic_budget':24,'widths':[16,64,256],'warmups':10,'samples':30,'processes':3,'seed':20261017,'b_seed':'20261017+N','timing':'full synchronized resident call; CPU ordering/layout and H2D excluded, recorded separately','null_control':'V1/V1 at three preselected configurations, 3 processes each','stop_before':'H-V'}}
    f=dest/'manifest.json'
    if f.exists():assert json.loads(f.read_text())==manifest,'Changed provenance; use a new result directory'
    else:save(f,manifest)
    status=dest/'progress.json';state=json.loads(status.read_text()) if status.exists() else {'version':'V2','state':'running','completed':[],'prepared':[]}
    if state['state']=='complete':print('ALREADY_COMPLETE_STOP_BEFORE_HV',flush=True);return
    state['state']='running';save(status,state)
    def stage(s):state['stage']=s;save(status,state);print(s,flush=True)
    def run(cmd,out,timeout=300):
        out.parent.mkdir(parents=True,exist_ok=True)
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
        out.with_suffix('.log').write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError(str(out)+' '+(r.stdout+r.stderr)[-3500:])
        x=json.loads(out.read_text());assert x['correctness'];return x
    try:
        stage('V2_SMOKE_PREPARATION');smoke_cases(dest)
        for m in [7,16,17,32,65]:
            for n in [33,64]:
                for cores in [1,24]:
                    out=dest/'smoke'/f'M{m}_N{n}_C{cores}.json'
                    if not(out.exists() and json.loads(out.read_text()).get('correctness')):
                        run([str(exe),str(ROOT/'cases_v2'/f'smoke_M{m}'/f'N{n}'),str(cores),'1','2','20261017',str(out),'V2'],out,90)
        stage('V2_SMOKE_PASS_20_OF_20')
        for source in files:
            stage('V2_ORDERING_'+source.stem);a=Matrix.load(str(source));od=dest/'orders'/source.stem;od.mkdir(parents=True,exist_ok=True)
            if (od/'order.bin').exists() and (od/'structure.json').exists():
                stats=json.loads((od/'structure.json').read_text());assert digest(od/'order.bin')==stats['order_sha256'];assert stats['input_sha256']==digest(source)
                order=np.fromfile(od/'order.bin',np.int32)
            else:
                order,stats=reorder(a,256,16,True);order.tofile(od/'order.bin')
                stats.update(matrix=source.stem,input_sha256=digest(source),order_sha256=digest(od/'order.bin'),m=a.shape[0],k=a.shape[1],nnz=len(a.col),moved_rows=int(np.sum(order!=np.arange(a.shape[0]))))
                save(od/'structure.json',stats)
            assert np.array_equal(np.sort(order),np.arange(a.shape[0]))
            stage('V2_LAYOUT_'+source.stem);t=time.perf_counter();plan=layout(a,order,{'w':16,'tail':[]},'V2');ls=time.perf_counter()-t
            original=json.loads((ROOT/'cases_v1'/source.stem/'N16/V1/metadata.json').read_text())
            stats.update(layout_seconds=ls,cube_groups=len(plan['cube_ptr'])-1,k16_tiles=len(plan['tiles']),v1_k16_tiles=original['k16_tiles'],tile_ratio_v1_over_v2=original['k16_tiles']/max(1,len(plan['tiles'])),tail_rows=a.shape[0]%16,tail_original_rows=order[-(a.shape[0]%16):].tolist() if a.shape[0]%16 else [],physical_density=len(a.col)/max(1,len(plan['tiles'])*256))
            save(od/'structure.json',stats)
            ref=csr_matrix((a.val.astype(np.float64),a.col,a.ptr),shape=a.shape)
            for n in [16,64,256]:
                base=ROOT/'cases_v0'/source.stem/f'N{n}'/'V0';out=ROOT/'cases_v2'/source.stem/f'N{n}'/'V2';marker=out/'metadata.json'
                if not marker.exists():
                    b=np.random.default_rng(20261017+n).uniform(-1,1,(a.shape[1],n)).astype(np.float16)
                    golden=(ref@b.astype(np.float64)).astype(np.float32)
                    export(a,plan,b,golden,out,stats|{'n':n,'b_seed':20261017+n,'order':'saved order.bin','w':16,'tail_policy':'zero_pad_to_16','full_output':True})
                meta=json.loads(marker.read_text());baseline=json.loads((base/'metadata.json').read_text())
                for key,h in meta['files_sha256'].items():assert digest(out/f'{key}.bin')==h
                for v in ['V0','V1']:
                    control=ROOT/f'cases_{v.lower()}'/source.stem/f'N{n}'/v
                    cm=json.loads((control/'metadata.json').read_text())
                    for key in ['rhs','golden','ptr','cols','values']:assert meta['files_sha256'][key]==cm['files_sha256'][key]
                    link=out.parent/v
                    if not link.exists():link.symlink_to(os.path.relpath(control,link.parent),target_is_directory=True)
                key=f'{source.stem}/N{n}'
                if key not in state['prepared']:state['prepared'].append(key)
                save(status,state)
            print('V2_PREPARED',source.stem,'ordering_seconds',round(stats['seconds'],3),'tile_ratio',round(stats['tile_ratio_v1_over_v2'],3),flush=True)
        stage('V2_NULL_CONTROLS')
        for name,n in [('SNAP_ca-HepTh',64),('SNAP_web-NotreDame',64),('Schmid_thermal1',256)]:
            for rep in range(3):
                key=f'null/{name}/N{n}/run{rep}'
                if key in state['completed']:continue
                out=dest/'null_control'/f'{name}_N{n}_run{rep}.json'
                run([str(exe),str(ROOT/'cases_v2'/name/f'N{n}'),'24','10','30',str(20261017+rep),str(out),'V1','V1'],out)
                state['completed'].append(key);state['last_completed']=key;save(status,state)
        jobs=[(rep,p.stem,n) for rep in range(3) for p in files for n in [16,64,256]];random.Random(20261017).shuffle(jobs)
        stage('V2_PAIRED_MEASUREMENTS')
        for rep,name,n in jobs:
            key=f'paired/{name}/N{n}/run{rep}'
            if key in state['completed']:continue
            out=dest/'measurements'/name/f'N{n}'/f'run{rep}.json'
            x=run([str(exe),str(ROOT/'cases_v2'/name/f'N{n}'),'24','10','30',str(20261017+rep),str(out),'V0','V1','V2'],out)
            assert [r['variant'] for r in x['records']]==['V0','V1','V2']
            state['completed'].append(key);state['last_completed']=key;save(status,state)
            print('V2_PAIRED_DONE',sum(s.startswith('paired/') for s in state['completed']),'/72',key,flush=True)
        rows=[]
        for source in files:
            for n in [16,64,256]:
                xs=[json.loads((dest/'measurements'/source.stem/f'N{n}'/f'run{r}.json').read_text()) for r in range(3)]
                row={'matrix':source.stem,'n':n,'v2_max_abs_error':max(x['records'][2]['max_abs_error'] for x in xs)}
                for i,v in enumerate(['v0','v1','v2']):
                    meds=[statistics.median(x['records'][i]['samples_us']) for x in xs];row[v+'_process_medians_us']=meds;row[v+'_median_us']=statistics.median(meds)
                for i,v in enumerate(['v0','v1']):
                    rr=[statistics.median([a/b for a,b in zip(x['records'][i]['samples_us'],x['records'][2]['samples_us'])]) for x in xs]
                    row[v+'_over_v2_per_process']=rr;row[v+'_over_v2']=statistics.median(rr)
                rows.append(row)
        save(dest/'summary.json',{'version':'V2','configurations':24,'paired_processes':72,'null_processes':9,'rows':rows,'correctness':True,'stop_before':'H-V'})
        state.update(state='complete',stage='V2_COMPLETE_STOP_BEFORE_HV',stop_required=True,next_version='H-V');save(status,state);print(state['stage'],flush=True)
    except BaseException:
        state.update(state='failed',error=traceback.format_exc());save(status,state);raise
if __name__=='__main__':main()
