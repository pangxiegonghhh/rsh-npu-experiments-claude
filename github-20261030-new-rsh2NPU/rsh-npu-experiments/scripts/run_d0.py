"""Resumable D0 only. No threshold changes, kernel changes, or D1 work."""
from __future__ import annotations
import argparse,fcntl,hashlib,json,math,os,platform,random,resource,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'results/d0'
POINTS=[('FEMLAB_ns3Da',16),('SNAP_email-Enron',64),('SNAP_ca-HepTh',256),('SNAP_web-NotreDame',16),('Schmid_thermal1',64)]
VARIANTS=['V0','V2','H-V','H-V'];SEED=20261018
BASE_SHA='508f4252df1cb3a73fa6872817622772563e82f00e01f8c8c2fd874969c7ef9d'
def read(p:Path)->dict:return json.loads(p.read_text())
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p:Path,x:dict)->None:
    p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp');tmp.write_text(json.dumps(x,indent=2)+'\n');tmp.replace(p)
def protocol()->dict:
    jobs=[{'matrix':m,'n':n,'rep':rep,'seed':SEED+rep} for rep in range(10) for m,n in POINTS]
    random.Random(SEED).shuffle(jobs)
    return {'schema':'rsh910b-d0-protocol-v1','points':POINTS,'jobs':jobs,'warmups':10,'repeats':30,'independent_processes_per_point':10,'variants':VARIANTS,'record_labels':['V0','V2','HV-A','HV-B'],'labels_are_record_indices':True,'primary':'V2/HV-A per-iteration paired ratio; per-process median; geomean over ten processes','secondary':['V0/HV-A','V2/HV-B','V0/HV-B'],'null':'HV-A/HV-B same implementation, separate allocations','interval':'20000 process-level bootstrap draws of mean log paired process ratios, fixed seed20261018; exploratory conditional interval, not population inference','noise_guard':'exp(q95(abs(log null process median ratio))); same process layer, descriptive','clear_positive_rule':'primary lower interval>1, primary geomean>noise_guard, at least8of10 process ratios>1, HV-B aggregate>1; descriptive signal, no significance claim','unresolved_rule':'otherwise retain result as weak/mixed/unresolved; never discard slow measurements','telemetry':'host per-call steady clock + bracketing thread CPU clock and CPU IDs; process resource stats; device/proc snapshots before and after each runner, never npu-smi within timed call','timer':'resident_synchronized_full_call_us','device_events':False,'fixed_parameters':{'W':16,'candidate_budget':256,'knn':16,'tau_nnz':4,'tau_inc':2,'long_row_split':False},'stop_after':'D0: recover/audit/backup then power off existing instance per user instruction','d1_authorized':False}
def running()->list[dict]:
    found=[]
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            pid=int(p.parent.name)
            if pid==os.getpid():continue
            args=p.read_bytes().decode(errors='replace').split('\0');first=Path(args[0]).name
            if first in ['rsh_runner','rsh_runner_d0','msprof'] or any(a.endswith('.py') and Path(a).name.startswith('run_') for a in args):found.append({'pid':pid,'argv':args})
        except (OSError,ValueError):pass
    return found
def probe()->dict:
    result={'time_ns':time.time_ns(),'monotonic_ns':time.monotonic_ns(),'hostname':platform.node(),'machine':platform.machine(),'pid':os.getpid(),'cpu_affinity':sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None}
    for name in ['loadavg','stat','meminfo','uptime']:
        p=Path('/proc')/name
        result['proc_'+name]=p.read_text() if p.exists() else None
    for label,cmd in [('npu_smi',['npu-smi','info']),('compiler',['g++','--version'])]:
        t=time.monotonic_ns()
        try:
            x=subprocess.run(cmd,capture_output=True,text=True,timeout=20);result[label]={'argv':cmd,'exit':x.returncode,'output':x.stdout+x.stderr,'probe_wall_ns':time.monotonic_ns()-t}
        except (OSError,subprocess.TimeoutExpired) as e:result[label]={'missing':str(e)}
    result['experiments']=running();result['free_disk_bytes']=shutil.disk_usage(ROOT).free
    return result
def validate(x:dict,warm:int,repeats:int,require_trace:bool=True)->None:
    assert x['correctness'] and x['warmups']==warm and x['repeats']==repeats
    assert [r['variant'] for r in x['records']]==VARIANTS
    assert x['timer']=='resident_synchronized_full_call_us' and x['b_rotation']==2
    for r in x['records']:
        assert r['valid_rows']==r['m'] and len(r['samples_us'])==repeats
        assert all(math.isfinite(t) and t>0 for t in r['samples_us'])
        assert math.isfinite(r['max_abs_error']) and r['max_abs_error']>=0
    a,b=x['records'][2:];assert all(a[k]==b[k] for k in ['m','k','n','cube_groups','k16_tiles','aiv_rows','valid_rows','max_abs_error'])
    if not require_trace:return
    assert x['host_trace_schema']=='d0-host-v1';trace=x['trace'];assert len(trace)==4*(warm+repeats)
    previous=0
    for iswarm,count in [(True,warm),(False,repeats)]:
        for i in range(count):
            subset=[t for t in trace if t['warm']==iswarm and t['iteration']==i]
            assert len(subset)==4 and sorted(t['record_index'] for t in subset)==list(range(4))
            assert [t['position'] for t in subset]==list(range(4))
            for t in subset:
                assert previous<=t['start_ns']<t['end_ns'] and t['thread_cpu_ns']>=0 and t['b_index']==i%2
                previous=t['end_ns']
                if not iswarm:
                    us=(t['end_ns']-t['start_ns'])/1000;record=x['records'][t['record_index']]['samples_us'][i]
                    assert abs(us-record)<=.02+1e-5*us,(us,record)
def freeze_cases()->dict:
    manifest={'files':{},'binary_files':{}}
    for m,n in POINTS:
        root=ROOT/'cases_hv'/m/f'N{n}'
        for v in ['V0','V2','H-V']:
            d=root/v;meta=read(d/'metadata.json');assert not meta.get('tail_skip_rows')
            for name in ['metadata.json','config.txt']:manifest['files'][str((d/name).relative_to(ROOT))]=sha(d/name)
            hashes=meta['files_sha256'];manifest['binary_files'][str(d.relative_to(ROOT))]=hashes
            assert set(hashes)=={'ptr','cols','values','cube_ptr','colref','tiles','rowmap','srows','rhs','golden','valid'}
            for key,h in hashes.items():assert sha(d/(key+'.bin'))==h,(m,n,v,key)
        metas=[read(root/v/'metadata.json') for v in ['V0','V2','H-V']]
        for key in ['ptr','cols','values','rhs','golden','valid']:assert len({x['files_sha256'][key] for x in metas})==1
    return manifest
def verify_cases(manifest:dict)->None:
    for p,h in manifest['files'].items():assert sha(ROOT/p)==h,p
    for p,hashes in manifest['binary_files'].items():
        for key,h in hashes.items():assert sha(ROOT/p/(key+'.bin'))==h,(p,key)
def smoke()->list[dict]:
    sys.path.insert(0,str(ROOT));import numpy as np
    from scipy.sparse import csr_matrix
    from rsh.planner import Matrix,partition,layout,execute_cpu
    from rsh.prepare import export
    cases=[]
    for name,m,n in [('short',7,33),('allzero',17,33),('disjoint',17,64),('dynamic',32,33)]:
        rng=np.random.default_rng(SEED+m);d=np.zeros((m,37),np.float16)
        if name=='short':d[:,:5]=rng.uniform(-1,1,(m,5));d[-1]=rng.uniform(-1,1,37)
        elif name=='disjoint':d[np.arange(m),np.arange(m)]=rng.uniform(.5,1,m)
        elif name=='dynamic':d[:,:5]=rng.uniform(-1,1,(m,5));d[0,1:]=0
        csr=csr_matrix(d.astype(np.float32));a=Matrix(csr.indptr.astype(np.int32),csr.indices.astype(np.int32),csr.data.astype(np.float16),csr.shape)
        order=np.arange(m,dtype=np.int32)[::-1].copy()
        if name=='dynamic':order=np.roll(order,1)
        split=partition(a,order,4,2,16);b=rng.uniform(-1,1,(37,n)).astype(np.float16);gold=(d.astype(np.float64)@b.astype(np.float64)).astype(np.float32)
        target=ROOT/'cases_d0'/('smoke_'+name)/f'N{n}'
        for v in ['V0','V2','H-V']:
            plan=layout(a,order,split,v);np.testing.assert_allclose(execute_cpu(a,plan,b),gold,atol=1e-3,rtol=1e-3)
            if not (target/v/'metadata.json').exists():export(a,plan,b,gold,target/v,{'kind':'D0_host_trace_smoke','order':order.tolist(),'split':split})
            meta=read(target/v/'metadata.json')
            for key,h in meta['files_sha256'].items():assert sha(target/v/(key+'.bin'))==h
        cases.append({'name':name,'m':m,'n':n,'root':str(target.relative_to(ROOT))})
    return cases

def main()->None:
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['prepare','measure','finish'],required=True);args=ap.parse_args()
    DEST.mkdir(exist_ok=True);lock=(DEST/'controller.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    protocol_path=DEST/'protocol.json'
    if protocol_path.exists():assert read(protocol_path)==json.loads(json.dumps(protocol()))
    else:save(protocol_path,protocol())
    state_path=DEST/'progress.json';state=read(state_path) if state_path.exists() else {'state':'initial','completed':[],'smoke':[],'stage':'initial','stop_required':True,'next':'none; D1 not started'}
    if state['state']=='complete':print('D0_ALREADY_COMPLETE_STOP',flush=True);return
    exe=ROOT/'build_d0/rsh_runner_d0'
    def stage(text:str)->None:state['stage']=text;save(state_path,state);print(text,flush=True)
    def run(root:Path,out:Path,cores:int,warm:int,repeats:int,seed:int,program:Path=exe)->None:
        if out.exists():validate(read(out),warm,repeats,program==exe);return
        out.parent.mkdir(parents=True,exist_ok=True);pending=out.with_name(out.stem+'.pending-'+str(time.time_ns())+'.json')
        before=probe();assert not before['experiments'],before['experiments'];save(out.with_suffix('.before.json'),before)
        cpu0=resource.getrusage(resource.RUSAGE_CHILDREN);start=time.monotonic_ns();epoch=time.time_ns()
        cmd=[str(program),str(root),str(cores),str(warm),str(repeats),str(seed),str(pending),*VARIANTS]
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        end=time.monotonic_ns();cpu1=resource.getrusage(resource.RUSAGE_CHILDREN)
        pending.with_suffix('.log').write_text(r.stdout+r.stderr)
        after=probe();save(out.with_suffix('.after.json'),after)
        save(out.with_suffix('.process.json'),{'argv':cmd,'start_epoch_ns':epoch,'start_monotonic_ns':start,'end_monotonic_ns':end,'exit':r.returncode,'child_user_seconds':cpu1.ru_utime-cpu0.ru_utime,'child_system_seconds':cpu1.ru_stime-cpu0.ru_stime,'child_voluntary_context_switches':cpu1.ru_nvcsw-cpu0.ru_nvcsw,'child_involuntary_context_switches':cpu1.ru_nivcsw-cpu0.ru_nivcsw,'max_rss_cumulative_children':cpu1.ru_maxrss,'monitor_scope':'before/after only; no background npu-smi during timed runner'})
        assert r.returncode==0,(pending,r.stdout[-1000:],r.stderr[-2000:]);validate(read(pending),warm,repeats,program==exe)
        assert not out.exists();pending.replace(out);pending.with_suffix('.log').replace(out.with_suffix('.log'))
    try:
        if args.phase=='prepare':
            state['state']='preparing';stage('D0_PREFLIGHT')
            env=probe();save(DEST/'preflight.json',env);assert not env['experiments'];assert env['machine']=='aarch64';assert env['npu_smi']['exit']==0
            assert sha(ROOT/'build_v4/rsh_runner')==BASE_SHA
            original=read(ROOT/'results/hv/manifest.json');assert original['executable_sha256']==BASE_SHA
            freeze=freeze_cases();fp=DEST/'case_manifest.json'
            if fp.exists():assert read(fp)==freeze
            else:save(fp,freeze)
            stage('D0_BUILD_HOST_ONLY')
            from scripts.prepare_d0 import build
            if not (DEST/'build.json').exists():build()
            assert sha(exe)==read(DEST/'build.json')['diagnostic_executable_sha256']
            (DEST/'device_binary').mkdir(exist_ok=True);shutil.copy2(exe,DEST/'device_binary/rsh_runner_d0')
            cases=smoke();save(DEST/'smoke_cases.json',{'cases':cases,'cpu_correctness':True})
            stage('D0_DEVICE_SMOKE')
            for c in cases:
                for cores in [1,24]:
                    for label,program in [('original',ROOT/'build_v4/rsh_runner'),('trace',exe)]:
                        key=f'{c["name"]}_C{cores}_{label}'
                        run(ROOT/c['root'],DEST/'smoke'/f'{key}.json',cores,1,2,SEED,program)
                        if key not in state['smoke']:state['smoke'].append(key)
                        save(state_path,state)
            state['state']='prepared';stage('D0_PREPARED_READY_FOR_MEASURE')
        elif args.phase=='measure':
            assert state['state'] in ['prepared','measuring','failed'] and len(state['smoke'])==16
            assert sha(exe)==read(DEST/'build.json')['diagnostic_executable_sha256'];verify_cases(read(DEST/'case_manifest.json'))
            source_paths=[p for p in (ROOT/'npu').glob('*') if p.is_file()]+[ROOT/'diagnostics/d0/runner.cpp']+[ROOT/'scripts'/name for name in ['prepare_d0.py','run_d0.py','analyze_d0.py']]
            frozen={'protocol_sha256':sha(DEST/'protocol.json'),'base_executable_sha256':sha(ROOT/'build_v4/rsh_runner'),'diagnostic_executable_sha256':sha(exe),'files':{str(p.relative_to(ROOT)):sha(p) for p in source_paths},'case_manifest_sha256':sha(DEST/'case_manifest.json'),'build_sha256':sha(DEST/'build.json')}
            mf=DEST/'manifest.json'
            if mf.exists():assert read(mf)==frozen,'Formal provenance changed'
            else:
                save(mf,frozen)
                for p in source_paths:
                    q=DEST/'source_snapshot'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
            state.pop('error',None)
            state['state']='measuring';stage('D0_FOURWAY_MEASUREMENTS')
            for job in protocol()['jobs']:
                m,n,rep,seed=job['matrix'],job['n'],job['rep'],job['seed'];key=f'{m}/N{n}/run{rep}'
                run(ROOT/'cases_hv'/m/f'N{n}',DEST/'measurements'/m/f'N{n}'/f'run{rep}.json',24,10,30,seed)
                if key not in state['completed']:state['completed'].append(key)
                state['last_completed']=key;save(state_path,state);print('D0_DONE',len(state['completed']),'/50',key,flush=True)
            state['state']='measurements_complete';stage('D0_MEASUREMENTS_COMPLETE_READY_FINISH')
        else:
            assert len(state['completed'])==len(set(state['completed']))==50
            assert set(state['completed'])=={f'{m}/N{n}/run{rep}' for m,n in POINTS for rep in range(10)}
            for m,n in POINTS:
                for rep in range(10):validate(read(DEST/'measurements'/m/f'N{n}'/f'run{rep}.json'),10,30)
            verify_cases(read(DEST/'case_manifest.json'));save(DEST/'final_environment.json',probe())
            assert not read(DEST/'final_environment.json')['experiments']
            state.update(state='complete',stage='D0_COMPLETE_STOP_BEFORE_D1',shutdown_required=True,local_recovery_audit_required=True);save(state_path,state);print(state['stage'],flush=True)
    except BaseException:
        state['state']='failed';state['error']=traceback.format_exc();save(state_path,state);raise
if __name__=='__main__':
    sys.path.insert(0,str(ROOT));main()
