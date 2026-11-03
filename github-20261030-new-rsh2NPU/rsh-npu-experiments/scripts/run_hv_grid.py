"""Conditional H-V-only 3-matrix, 9-threshold follow-up; defaults sealed."""
from pathlib import Path
import argparse,json,math,os,random,statistics,subprocess,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.hv_cases import digest,save,check_split
from rsh.planner import Matrix,partition,layout
from rsh.prepare import export
DEV=['SNAP_ca-HepTh','SNAP_email-Enron','HB_bcsstk17']
GRID=[(4,2)]+[(a,b) for a in [2,4,8] for b in [1,2,4] if (a,b)!=(4,2)]

def prepare(name: str,n: int,tau: tuple[int,int])->Path:
    dest=ROOT/'results/hv/grid';a=Matrix.load(str(ROOT/'inputs'/f'{name}.npz'));order=np.fromfile(ROOT/'results/v2/orders'/name/'order.bin',np.int32);td=f't{tau[0]}_{tau[1]}'
    root=ROOT/'cases_hv_grid'/td/name/f'N{n}';target=root/'H-V';marker=target/'metadata.json'
    if not marker.exists():
        t=time.perf_counter();split=partition(a,order,tau[0],tau[1],16);seconds=time.perf_counter()-t;check_split(a,split);plan=layout(a,order,split,'H-V')
        pd=dest/'plans'/td/name;save(pd/'routing.json',{'matrix':name,'tau_nnz':tau[0],'tau_inc':tau[1],'n':n,'order_sha256':digest(ROOT/'results/v2/orders'/name/'order.bin'),'split':split})
        base=ROOT/'cases_v0'/name/f'N{n}/V0';stride=(n+15)//16*16;b=np.fromfile(base/'rhs.bin',np.float16).reshape(a.shape[1]+1,stride)[:a.shape[1],:n];gold=np.fromfile(base/'golden.bin',np.float32).reshape(a.shape[0],stride)[:,:n]
        export(a,plan,b,gold,target,{'matrix':name,'n':n,'tau_nnz':tau[0],'tau_inc':tau[1],'partition_seconds':seconds,'routing_sha256':digest(pd/'routing.json'),'full_output':True,'tail_policy':'AIV','cube_groups':len(split['groups']),'k16_tiles':len(plan['tiles']),'aiv_rows':len(plan['srows'])})
    meta=json.loads(marker.read_text());base=json.loads((ROOT/'cases_hv'/name/f'N{n}/H-V/metadata.json').read_text())
    for key,h in meta['files_sha256'].items():assert digest(target/f'{key}.bin')==h
    for key in ['ptr','cols','values','rhs','golden']:assert meta['files_sha256'][key]==base['files_sha256'][key]
    for v,control in [('V0',ROOT/'cases_v0'/name/f'N{n}/V0'),('V2',ROOT/'cases_v2'/name/f'N{n}/V2'),('H-V-base',ROOT/'cases_hv'/name/f'N{n}/H-V')]:
        link=root/v
        if not link.exists():link.symlink_to(os.path.relpath(control,root),target_is_directory=True)
    return root

def main()->None:
    dest=ROOT/'results/hv';decision=json.loads((dest/'threshold_decision.json').read_text());assert decision['triggered'] and not decision['resolved'];n=decision['n'];grid=dest/'grid';grid.mkdir(exist_ok=True);exe=ROOT/'build_v4/rsh_runner'
    mf={'controller_sha256':digest(Path(__file__)),'source_hashes':{f:digest(ROOT/f) for f in ['rsh/planner.py','rsh/prepare.py']},'executable_sha256':digest(exe),'development_matrices':DEV,'n':n,'grid':GRID,'warmups':10,'samples':30,'processes':3,'seed':20261017,'selection':'minimum geometric mean full latency across three dev matrices; prefer default unless each process aggregate paired improvement exceeds global null p95; no Skip selection','stop_before':'H-C'}
    # JSON represents tuples as lists.
    mf=json.loads(json.dumps(mf));mp=grid/'manifest.json'
    if mp.exists():assert json.loads(mp.read_text())==mf
    else:save(mp,mf)
    sp=grid/'progress.json';s=json.loads(sp.read_text()) if sp.exists() else {'state':'running','completed':[]};s['state']='running';save(sp,s)
    try:
        for tau in GRID[1:]:
            for name in DEV:prepare(name,n,tau)
        jobs=[(rep,name,tau) for rep in range(3) for name in DEV for tau in GRID[1:]];random.Random(20261017).shuffle(jobs)
        for rep,name,tau in jobs:
            td=f't{tau[0]}_{tau[1]}';key=f'{td}/{name}/run{rep}'
            if key in s['completed']:continue
            root=ROOT/'cases_hv_grid'/td/name/f'N{n}';out=grid/'measurements'/td/name/f'run{rep}.json';out.parent.mkdir(parents=True,exist_ok=True)
            cmd=[str(exe),str(root),'24','10','30',str(20261017+rep),str(out),'V0','V2','H-V-base','H-V'];r=subprocess.run(cmd,capture_output=True,text=True,timeout=300);out.with_suffix('.log').write_text(r.stdout+r.stderr)
            if r.returncode:raise RuntimeError(key+' '+(r.stdout+r.stderr)[-2500:])
            x=json.loads(out.read_text());assert x['correctness'] and [r['variant'] for r in x['records']]==['V0','V2','H-V-base','H-V'];s['completed'].append(key);s['last_completed']=key;save(sp,s);print('HV_GRID_DONE',len(s['completed']),'/72',key,flush=True)
        options=[]
        for tau in GRID:
            td=f't{tau[0]}_{tau[1]}';meds=[];gains=[]
            for rep in range(3):
                lat=[];rat=[]
                for name in DEV:
                    if tau==(4,2):x=json.loads((dest/'measurements'/name/f'N{n}'/f'run{rep}.json').read_text());ts=x['records'][2]['samples_us'];rr=1.
                    else:
                        x=json.loads((grid/'measurements'/td/name/f'run{rep}.json').read_text());ts=x['records'][3]['samples_us'];rr=statistics.median(a/b for a,b in zip(x['records'][2]['samples_us'],ts))
                    lat.append(statistics.median(ts));rat.append(rr)
                meds.append(math.exp(statistics.mean(math.log(t) for t in lat)));gains.append(math.exp(statistics.mean(math.log(t) for t in rat)))
            options.append({'tau_nnz':tau[0],'tau_inc':tau[1],'aggregate_latency_per_process_us':meds,'aggregate_latency_us':statistics.median(meds),'paired_default_over_candidate_per_process':gains})
        best=min(options,key=lambda x:(x['aggregate_latency_us'],GRID.index((x['tau_nnz'],x['tau_inc']))));selected=best if all(t>decision['null_p95_ratio'] for t in best['paired_default_over_candidate_per_process']) else options[0]
        save(grid/'summary.json',{'correctness':True,'new_configurations':24,'reused_default_configurations':3,'processes':72,'n':n,'options':options,'lowest_measured_latency':best,'selected_public_configuration':selected,'default_retained':selected==options[0],'selection_noise_limit':decision['null_p95_ratio'],'limits':'Exploratory grid; descriptive noise guard is not a significance test. Default retained when improvements are small or inconsistent. No per-instance winner treated as default.'})
        s.update(state='complete',stop_required=True);save(sp,s)
        decision.update(resolved=True,grid_complete=True,selected_tau_nnz=selected['tau_nnz'],selected_tau_inc=selected['tau_inc'],default_retained=selected==options[0],holdout_evaluation_required=selected!=options[0]);save(dest/'threshold_decision.json',decision);print('HV_GRID_COMPLETE',selected['tau_nnz'],selected['tau_inc'],flush=True)
    except BaseException:s.update(state='failed',error=traceback.format_exc());save(sp,s);raise
if __name__=='__main__':main()
