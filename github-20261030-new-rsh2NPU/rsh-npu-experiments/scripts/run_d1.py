"""Resumable D1 only: frozen layouts, uninstrumented full call, separate events."""
from __future__ import annotations
import argparse,fcntl,json,math,os,random,resource,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1 import POINTS,ARGS,LABELS,KEYS,sha,read,save,transform,alias,cases,build
from scripts.run_d0 import probe as old_probe,running
D=ROOT/'results/d1';SEED=20261018

def protocol():
    jobs=[{'matrix':m,'n':n,'rep':r,'seed':SEED+1000+r} for r in range(10) for m,n in POINTS];random.Random(SEED+1).shuffle(jobs)
    events=[{'matrix':m,'n':n,'rep':r,'seed':SEED+2000+r} for r in range(3) for m,n in POINTS];random.Random(SEED+2).shuffle(events)
    return {'schema':'d1-protocol-v1','points':POINTS,'args':ARGS,'labels':LABELS,'label_mapping':'record index; nested basename chooses original kernel kind','jobs':jobs,'event_jobs':events,'warmups':10,'repeats':30,'formal_processes_per_point':10,'event_processes_per_point':3,'formal_program':'build_d0/rsh_runner_d0','formal_sha256':'811c04e912ddb6e6ec385ede6661115a335b1ac8f024621edae4640d8b6c3973','primary_contrasts':['V2/V2-Z','V2-Z/HV-A','V2/HV-A'],'secondary':['V0/HV-A','V2/HV-B','V2-Z/HV-B'],'null':'HV-A/HV-B independent allocations same implementation','stats':'process median of 30 paired iteration ratios; geomean of 10 processes; 20000 process bootstrap seed20261018; descriptive guard exp(q95(abs(log null process ratios)))','clear_rule':'lower conditional bootstrap bound>1; aggregate>guard; >=8/10 positive; HV-B direction confirms when denominator is HV-A','device_events':'five ACL_EVENT_TIME_LINE events; four adjacent intervals+total; queries outside recorded host wall; one stream sync; separate diagnostic executable','event_reporting':'median over samples per process then median across 3 processes; report process values; events affect execution, do not use profile wall for official acceleration','full_output_labels':LABELS[:5],'partial_output_labels':LABELS[5:],'G_ST_rule':'frozen HV ownership; validate owned rows only, empty scope explicitly reported; never claim full SpMM or infer overlap from sum/max','single_factor':'V2-Z removes whole zero-K groups and packed/restore slots only; all nonempty group data/order identical; whole M output clear preserved','B_gather':'inside main; not isolated pure compute','thresholds':[4,2],'W':16,'candidate_budget':256,'knn':16,'long_row_split':False,'stop_after':'D1 recover/audit/backup then power off, no D2/D3'}

def probe():
    x=old_probe();x['experiments']=[p for p in x['experiments'] if p['pid']!=os.getpid()]
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            a=p.read_bytes().decode(errors='replace').split('\0');pid=int(p.parent.name)
            if pid!=os.getpid() and Path(a[0]).name=='rsh_runner_profile':x['experiments'].append({'pid':pid,'argv':a})
        except (OSError,ValueError):pass
    return x

def validate(x,warm,repeats,event=False,root=None):
    assert x['correctness'] and x['warmups']==warm and x['repeats']==repeats
    assert [r['variant'] for r in x['records']]==['V0','V2','V2','H-V','H-V','V2','V0']
    assert x['timer']=='resident_synchronized_full_call_us' and x['b_rotation']==2
    for i,r in enumerate(x['records']):
        assert len(r['samples_us'])==repeats and all(math.isfinite(t) and t>0 for t in r['samples_us'])
        assert math.isfinite(r['max_abs_error']) and r['max_abs_error']>=0
        if i<5:assert r['valid_rows']==r['m']
        if root:
            import numpy as np
            cfg=list(map(int,(root/ARGS[i]/'config.txt').read_text().split()));v=np.fromfile(root/ARGS[i]/'valid.bin',np.uint8)
            assert (r['m'],r['k'],r['n'],r['cube_groups'],r['k16_tiles'],r['aiv_rows'],r['valid_rows'])==(cfg[0],cfg[1],cfg[2],cfg[5],cfg[6],cfg[7],int(v.sum()))
    for k in ['m','k','n','cube_groups','k16_tiles','aiv_rows','valid_rows','max_abs_error']:assert x['records'][3][k]==x['records'][4][k]
    trace=x['trace'];assert len(trace)==7*(warm+repeats);previous=0
    for iswarm,count in [(True,warm),(False,repeats)]:
        for i in range(count):
            subset=[t for t in trace if t['warm']==iswarm and t['iteration']==i]
            assert len(subset)==7 and sorted(t['record_index'] for t in subset)==list(range(7)) and [t['position'] for t in subset]==list(range(7))
            for t in subset:
                assert previous<=t['start_ns']<t['end_ns'] and t['thread_cpu_ns']>=0 and t['b_index']==i%2;previous=t['end_ns']
                if not iswarm:
                    us=(t['end_ns']-t['start_ns'])/1000;v=x['records'][t['record_index']]['samples_us'][i];assert abs(us-v)<=.02+1e-5*us
    if event:
        assert x['event_schema']=='d1-timeline-v1' and len(x['events'])==7
        for rows in x['events']:
            assert len(rows)==repeats
            for v in rows:
                assert len(v)==5 and all(math.isfinite(t) and t>=0 for t in v) and v[-1]>0
                assert abs(sum(v[:4])-v[4])<.03+1e-4*v[4],v
    else:assert 'events' not in x

def freeze(roots):
    index={'files':{},'roots':roots}
    for root in roots:
        for arg in sorted(set(ARGS)):
            d=ROOT/root/arg
            for name in ['metadata.json','config.txt']+[k+'.bin' for k in KEYS]:index['files'][str((d/name).relative_to(ROOT))]=sha(d/name)
    return index

def verify(index):
    for p,h in index['files'].items():assert sha(ROOT/p)==h,p

def smoke():
    from scripts.run_d0 import smoke as base_smoke
    from rsh.planner import Matrix,execute_cpu
    import numpy as np
    out=[]
    for c in base_smoke():
        src=ROOT/c['root'];dst=ROOT/'cases_d1'/('smoke_'+c['name'])/f'N{c["n"]}'
        for v in ['V0','V2','H-V']:alias(src/v,dst/v)
        for name,source,mode in [('V2-Z/V2','V2','Z'),('G-only/V2','H-V','G'),('ST-only/V0','H-V','ST')]:transform(src/source,dst/name,mode)
        cfg=list(map(int,(dst/'V0/config.txt').read_text().split()));m,k,n,st,nnz=cfg[:5]
        a=Matrix(np.fromfile(dst/'V0/ptr.bin',np.int32),np.fromfile(dst/'V0/cols.bin',np.int32),np.fromfile(dst/'V0/values.bin',np.float16),(m,k));b=np.fromfile(dst/'V0/rhs.bin',np.float16).reshape(k+1,st)[:k,:n];gold=np.fromfile(dst/'V0/golden.bin',np.float32).reshape(m,st)[:,:n]
        for arg in set(ARGS):
            d=dst/arg;plan={q:np.fromfile(d/(q+'.bin'),dt) for q,dt in [('cube_ptr',np.int64),('colref',np.int32),('rowmap',np.int32),('srows',np.int32),('valid',np.uint8)]};plan['tiles']=np.fromfile(d/'tiles.bin',np.float16).reshape(-1,16,16)
            y=execute_cpu(a,plan,b);keep=plan['valid'].astype(bool);np.testing.assert_allclose(y[keep],gold[keep],atol=1e-3,rtol=1e-3)
        out.append(c|{'root':str(dst.relative_to(ROOT))})
    save(D/'smoke_cases.json',{'cpu_correctness':True,'cases':out});return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['prepare','measure','profile','finish'],required=True);arg=ap.parse_args();D.mkdir(exist_ok=True)
    lock=(D/'controller.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    p=D/'protocol.json'
    if p.exists():assert read(p)==json.loads(json.dumps(protocol()))
    else:save(p,protocol())
    state=read(D/'progress.json') if (D/'progress.json').exists() else {'state':'initial','completed':[],'profile_completed':[],'smoke':[],'stage':'initial'}
    def stage(s):state['stage']=s;save(D/'progress.json',state);print(s,flush=True)
    def run(root,out,cores,warm,repeats,seed,event=False):
        if out.exists():validate(read(out),warm,repeats,event,root);return
        exe=ROOT/('build_d1/rsh_runner_profile' if event else 'build_d0/rsh_runner_d0');expected=read(D/'build.json')['event_executable_sha256'] if event else protocol()['formal_sha256'];assert sha(exe)==expected
        out.parent.mkdir(parents=True,exist_ok=True);pending=out.with_name(out.stem+'.pending-'+str(time.time_ns())+'.json')
        before=probe();assert not before['experiments'],before['experiments'];save(out.with_suffix('.before.json'),before)
        cmd=[str(exe),str(root),str(cores),str(warm),str(repeats),str(seed),str(pending),*ARGS]
        t=time.monotonic_ns();epoch=time.time_ns();cpu=resource.getrusage(resource.RUSAGE_CHILDREN);r=subprocess.run(cmd,capture_output=True,text=True,timeout=300);e=time.monotonic_ns();cpu1=resource.getrusage(resource.RUSAGE_CHILDREN)
        pending.with_suffix('.log').write_text(r.stdout+r.stderr);save(out.with_suffix('.after.json'),probe());save(out.with_suffix('.process.json'),{'argv':cmd,'start_epoch_ns':epoch,'start_monotonic_ns':t,'end_monotonic_ns':e,'exit':r.returncode,'event':event,'child_user_seconds':cpu1.ru_utime-cpu.ru_utime,'child_system_seconds':cpu1.ru_stime-cpu.ru_stime,'monitor_scope':'before/after runner, no continuous probes during timed calls'})
        assert r.returncode==0,(pending,r.stdout[-1000:],r.stderr[-3000:]);validate(read(pending),warm,repeats,event,root);pending.replace(out);pending.with_suffix('.log').replace(out.with_suffix('.log'))
    if state['state']=='complete':print('D1_ALREADY_COMPLETE_STOP');return
    try:
        if arg.phase=='prepare':
            stage('D1_PREFLIGHT');save(D/'preflight.json',probe());assert not read(D/'preflight.json')['experiments'];assert sha(ROOT/'build_d0/rsh_runner_d0')==protocol()['formal_sha256']
            stage('D1_BUILD_LAYOUTS_AND_EVENT_HOST');facts=cases();build();small=smoke()
            index=freeze([p['root'] for p in facts]+[p['root'] for p in small]);save(D/'case_manifest.json',index)
            stage('D1_DEVICE_SMOKE')
            for c in small:
                for cores in [1,24]:
                    for event in [False,True]:
                        key=f'{c["name"]}_C{cores}_'+('event' if event else 'formal');run(ROOT/c['root'],D/'smoke'/f'{key}.json',cores,1,2,SEED,event)
                        if key not in state['smoke']:state['smoke'].append(key)
                        save(D/'progress.json',state)
            state['state']='prepared';stage('D1_PREPARED')
        elif arg.phase in ['measure','profile']:
            assert len(state['smoke'])==16;verify(read(D/'case_manifest.json'))
            source=[p for p in (ROOT/'npu').glob('*') if p.is_file()]+[ROOT/p for p in ['scripts/prepare_d1.py','scripts/run_d1.py','scripts/analyze_d1.py','scripts/audit_d1.py','diagnostics/d1/profile_runner.cpp']]
            frozen={'files':{str(p.relative_to(ROOT)):sha(p) for p in source},'case_manifest_sha256':sha(D/'case_manifest.json'),'protocol_sha256':sha(D/'protocol.json'),'build_sha256':sha(D/'build.json')}
            if (D/'manifest.json').exists():assert read(D/'manifest.json')==frozen
            else:
                save(D/'manifest.json',frozen)
                for p in source:
                    q=D/'source_snapshot'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
            event=arg.phase=='profile'
            if event:assert len(state['completed'])==50
            state['state']='profiling' if event else 'measuring';state.pop('error',None);stage('D1_EVENT_DIAGNOSTICS' if event else 'D1_FORMAL_SEVENWAY')
            jobs=protocol()['event_jobs'] if event else protocol()['jobs'];field='profile_completed' if event else 'completed';folder='profile' if event else 'measurements'
            for job in jobs:
                m,n,r,seed=job['matrix'],job['n'],job['rep'],job['seed'];key=f'{m}/N{n}/run{r}'
                run(ROOT/'cases_d1'/m/f'N{n}',D/folder/m/f'N{n}'/f'run{r}.json',24,10,30,seed,event)
                if key not in state[field]:state[field].append(key)
                state['last_completed']=folder+'/'+key;save(D/'progress.json',state);print('D1_DONE',folder,len(state[field]),'/',len(jobs),key,flush=True)
            state['state']='profile_complete' if event else 'measurements_complete';stage('D1_'+state['state'].upper())
        else:
            assert len(set(state['completed']))==50 and len(set(state['profile_completed']))==15
            for event,reps,folder in [(False,10,'measurements'),(True,3,'profile')]:
                for m,n in POINTS:
                    for r in range(reps):validate(read(D/folder/m/f'N{n}'/f'run{r}.json'),10,30,event,ROOT/'cases_d1'/m/f'N{n}')
            verify(read(D/'case_manifest.json'));save(D/'final_environment.json',probe());assert not read(D/'final_environment.json')['experiments'];state.update(state='complete',stage='D1_COMPLETE_STOP_BEFORE_D2',shutdown_required=True,local_recovery_audit_required=True);save(D/'progress.json',state);print(state['stage'],flush=True)
    except BaseException:
        state['state']='failed';state['error']=traceback.format_exc();save(D/'progress.json',state);raise
if __name__=='__main__':main()
