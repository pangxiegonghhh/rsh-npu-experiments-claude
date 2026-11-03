"""D1b only: native clear substitution with identical compute objects and data."""
from __future__ import annotations
import argparse,fcntl,json,math,os,random,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1b import POINTS,ARGS,LABELS,sha,read,save,cases,build
from scripts.run_d1 import probe as prior_probe
D=ROOT/'results/d1b';SEED=20261019
SMOKE_ARGS=ARGS+['old/G-only/V2','new/G-only/V2','old/ST-only/V0','new/ST-only/V0']

def protocol():
    jobs=[{'matrix':m,'n':n,'rep':r,'seed':SEED+r} for r in range(10) for m,n in POINTS];random.Random(SEED).shuffle(jobs)
    profiles=[{'matrix':m,'n':n,'rep':r,'seed':SEED+1000+r} for r in range(3) for m,n in POINTS];random.Random(SEED+1).shuffle(profiles)
    return {'schema':'d1b-protocol-v1','points':POINTS,'args':ARGS,'labels':LABELS,'jobs':jobs,'profiles':profiles,'warmups':10,'repeats':30,'formal_processes_per_point':10,'profile_processes_per_point':3,'single_factor':'replace each required full buffer aclrtMemsetAsync with separate same-stream AIV zero kernel; no clear deletion/fusion, no compute change','formal_device_events':False,'formal_comparison':'old/new branches in same newly linked host executable and same randomized per-iteration order; same SpMM objects, different allocations','null':'New-HV-A/New-HV-B exact same implementation, separate allocations','stats':'per-process median of 30 iteration paired ratios; geomean across10; conditional bootstrap20000 seed20261019; descriptive guard exp(q95(abs(log null process ratios)))','clear_positive_rule':'conditional lower>1, geomean>guard, >=8/10 ratios>1; new HV-B direction confirmation reported separately','correctness':'B/-B, full output, all padded cols and unowned partial rows must zero; standalone finite/NaN poison guard tests for zero kernel','partial_smoke_args':SMOKE_ARGS,'fixed':{'W':16,'candidate_budget':256,'knn':16,'thresholds':[4,2],'long_row_split':False},'smoke':'four frozen D1 cases, original/new host at cores1/24; original ignores flags and uses runtime memset for every record','stop_after':'D1b recover/audit/save then verified poweroff; no D2'}

def probe():
    x=prior_probe()
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            argv=p.read_bytes().decode(errors='replace').split('\0');pid=int(p.parent.name)
            if pid!=os.getpid() and Path(argv[0]).name.startswith('rsh_runner_d1b'):x['experiments'].append({'pid':pid,'argv':argv})
        except (OSError,ValueError):pass
    return x

def validate(x,warm,repeats,event=False,smoke=False,native_field=True):
    args=SMOKE_ARGS if smoke else ARGS;count=len(args);names=[Path(a).name for a in args]
    assert x['correctness'] and x['warmups']==warm and x['repeats']==repeats and [r['variant'] for r in x['records']]==names
    assert x['b_rotation']==2 and x['timer']=='resident_synchronized_full_call_us'
    for i,(arg,r) in enumerate(zip(args,x['records'])):
        assert len(r['samples_us'])==repeats and all(math.isfinite(v) and v>0 for v in r['samples_us']);assert math.isfinite(r['max_abs_error']) and r['max_abs_error']>=0
        if i<9:assert r['valid_rows']==r['m']
        if native_field:assert r['native_clear']==arg.startswith('new/')
    for i,j in [(0,1),(2,3),(4,5),(6,7),(7,8)]+([(9,10),(11,12)] if smoke else []):
        for k in ['m','k','n','cube_groups','k16_tiles','aiv_rows','valid_rows','max_abs_error']:assert x['records'][i][k]==x['records'][j][k],(i,j,k)
    # The original host lacks tracing only when explicitly using its pre-D0 executable; D0 has host trace.
    tr=x['trace'];assert len(tr)==count*(warm+repeats);previous=0
    for iswarm,length in [(True,warm),(False,repeats)]:
        for i in range(length):
            subset=[t for t in tr if t['warm']==iswarm and t['iteration']==i];assert len(subset)==count and sorted(t['record_index'] for t in subset)==list(range(count));assert [t['position'] for t in subset]==list(range(count))
            for t in subset:
                assert previous<=t['start_ns']<t['end_ns'] and t['b_index']==i%2 and t['thread_cpu_ns']>=0;previous=t['end_ns']
                if not iswarm:
                    us=(t['end_ns']-t['start_ns'])/1000;assert abs(us-x['records'][t['record_index']]['samples_us'][i])<=.02+1e-5*us
    if event:
        assert x['event_schema']=='d1-timeline-v1' and x['host_api_schema']=='d1-api-v1' and len(x['events'])==len(x['host_api_us'])==count
        for i in range(count):
            assert len(x['events'][i])==len(x['host_api_us'][i])==repeats
            for e,h,w in zip(x['events'][i],x['host_api_us'][i],x['records'][i]['samples_us']):
                assert len(e)==5 and len(h)==10 and all(math.isfinite(v) and v>=0 for v in e+h) and e[-1]>0
                assert abs(sum(e[:4])-e[4])<.03+1e-4*e[4] and sum(h)<=w+.1
    else:assert 'events' not in x

def verify_cases():
    for p,h in read(D/'case_manifest.json')['files'].items():assert sha(ROOT/p)==h,p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['prepare','measure','profile','finish'],required=True);a=ap.parse_args();D.mkdir(exist_ok=True)
    lock=(D/'controller.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (D/'protocol.json').exists():assert read(D/'protocol.json')==json.loads(json.dumps(protocol()))
    else:save(D/'protocol.json',protocol())
    state=read(D/'progress.json') if (D/'progress.json').exists() else {'state':'initial','completed':[],'profile_completed':[],'smoke':[]}
    def stage(s):state['stage']=s;save(D/'progress.json',state);print(s,flush=True)
    def run(root,out,cores,warm,repeats,seed,event=False,smoke=False,old=False):
        if out.exists():validate(read(out),warm,repeats,event,smoke,not old);return
        info=read(D/'build.json')['executables']['profile' if event else 'formal'];exe=ROOT/info['path']
        if old:exe=ROOT/'build_d0/rsh_runner_d0';assert sha(exe)=='811c04e912ddb6e6ec385ede6661115a335b1ac8f024621edae4640d8b6c3973'
        else:assert sha(exe)==info['sha256']
        out.parent.mkdir(parents=True,exist_ok=True);pending=out.with_name(out.stem+'.pending-'+str(time.time_ns())+'.json');env=probe();assert not env['experiments'],env['experiments'];save(out.with_suffix('.before.json'),env)
        args=SMOKE_ARGS if smoke else ARGS;cmd=[str(exe),str(root),str(cores),str(warm),str(repeats),str(seed),str(pending),*args];start=time.monotonic_ns();p=subprocess.run(cmd,capture_output=True,text=True,timeout=300);end=time.monotonic_ns();pending.with_suffix('.log').write_text(p.stdout+p.stderr);save(out.with_suffix('.after.json'),probe());save(out.with_suffix('.process.json'),{'argv':cmd,'exit':p.returncode,'event':event,'old_program':old,'start_monotonic_ns':start,'end_monotonic_ns':end})
        assert p.returncode==0,(pending,p.stderr[-3000:]);validate(read(pending),warm,repeats,event,smoke,not old);pending.replace(out);pending.with_suffix('.log').replace(out.with_suffix('.log'))
    if state['state']=='complete':print('D1b_ALREADY_COMPLETE_STOP');return
    try:
        if a.phase=='prepare':
            stage('D1b_PREFLIGHT');save(D/'preflight.json',probe());assert not read(D/'preflight.json')['experiments'];assert read(D/'preflight.json')['machine']=='aarch64'
            stage('D1b_BUILD_ZERO_ONLY');cases();build()
            stage('D1b_ZERO_GUARD_PROBE');info=read(D/'build.json')['executables']['zero_probe'];p=subprocess.run([str(ROOT/info['path']),str(D/'zero_probe.json')],capture_output=True,text=True,timeout=300);(D/'zero_probe.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr;assert read(D/'zero_probe.json')['tests']==40
            stage('D1b_DEVICE_SMOKE')
            small=[p for p in read(D/'case_manifest.json')['roots'] if Path(p).parent.name.startswith('smoke_')]
            for root in small:
                for cores in [1,24]:
                    for label,event,old in [('d0control',False,True),('formal',False,False),('profile',True,False)]:
                        key=Path(root).parent.name+f'_C{cores}_'+label;run(ROOT/root,D/'smoke'/f'{key}.json',cores,1,2,SEED,event,True,old)
                        if key not in state['smoke']:state['smoke'].append(key)
                        save(D/'progress.json',state)
            state['state']='prepared';stage('D1b_PREPARED')
        elif a.phase in ['measure','profile']:
            assert len(state['smoke'])==24;verify_cases();event=a.phase=='profile'
            source=[p for p in (ROOT/'diagnostics/d1b').glob('*') if p.is_file()]+[ROOT/'scripts'/name for name in ['prepare_d1b.py','run_d1b.py','analyze_d1b.py','audit_d1b.py']]+[ROOT/'npu'/name for name in ['runner.cpp','dispatch.cpp','common.h','cube.cpp','vector.cpp','mix.cpp','restore.cpp','work.h']]
            frozen={'files':{str(p.relative_to(ROOT)):sha(p) for p in source},'protocol_sha256':sha(D/'protocol.json'),'case_manifest_sha256':sha(D/'case_manifest.json'),'build_sha256':sha(D/'build.json')}
            if (D/'manifest.json').exists():assert read(D/'manifest.json')==frozen
            else:
                save(D/'manifest.json',frozen)
                for p in source:q=D/'source_snapshot'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
            if event:assert len(state['completed'])==50
            state['state']='profiling' if event else 'measuring';state.pop('error',None);stage('D1b_PROFILE' if event else 'D1b_FORMAL')
            field='profile_completed' if event else 'completed';folder='profile' if event else 'measurements';jobs=protocol()['profiles'] if event else protocol()['jobs']
            for job in jobs:
                m,n,rep,seed=job['matrix'],job['n'],job['rep'],job['seed'];key=f'{m}/N{n}/run{rep}';run(ROOT/'cases_d1b'/m/f'N{n}',D/folder/m/f'N{n}'/f'run{rep}.json',24,10,30,seed,event)
                if key not in state[field]:state[field].append(key)
                save(D/'progress.json',state);print('D1b_DONE',folder,len(state[field]),'/',len(jobs),key,flush=True)
            state['state']='profile_complete' if event else 'measurements_complete';stage('D1b_'+state['state'].upper())
        else:
            assert len(set(state['completed']))==50 and len(set(state['profile_completed']))==15
            for event,count,folder in [(False,10,'measurements'),(True,3,'profile')]:
                for m,n in POINTS:
                    for rep in range(count):validate(read(D/folder/m/f'N{n}'/f'run{rep}.json'),10,30,event)
            verify_cases();save(D/'final_environment.json',probe());assert not read(D/'final_environment.json')['experiments'];state.update(state='complete',stage='D1b_COMPLETE_STOP_BEFORE_D2',shutdown_required=True,local_recovery_audit_required=True);save(D/'progress.json',state);print(state['stage'],flush=True)
    except BaseException:
        state['state']='failed';state['error']=traceback.format_exc();save(D/'progress.json',state);raise
if __name__=='__main__':main()
