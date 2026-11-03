"""D2 resumable controller. Native backend frozen; no D3 actions."""
from __future__ import annotations
import argparse,fcntl,json,math,os,random,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d2 import DEV,EVAL,ARGS,LABELS,PROFILE_ARGS,PROFILE_LABELS,sha,read,save,prepare,build
from scripts.run_d1b import probe as prior_probe
D=ROOT/'results/d2';SEED=20261029

def protocol():
    def jobs(points,count,seed):
        x=[dict(matrix=m,n=n,rep=r,seed=seed+r) for r in range(count) for m,n in points];random.Random(seed+71).shuffle(x);return x
    dev=[(m,64) for m in DEV];ev=[(m,n) for m in EVAL for n in [16,64,256]]
    return dict(schema='d2-protocol-v1',dev_points=dev,eval_points=ev,args=ARGS,labels=LABELS,profile_args=PROFILE_ARGS,profile_labels=PROFILE_LABELS,dev_jobs=jobs(dev,10,SEED),dev_profiles=jobs(dev,3,SEED+1000),eval_jobs=jobs(ev,10,SEED+2000),eval_profiles=jobs(ev,3,SEED+3000),warmups=10,repeats=30,cores=24,backend='D1b native AIV zero; both full required clears retained',allocation='shuffle construction outside timings; seed xor 0x5A17B39D, independent RNG from per-iteration order',primary='Per point/process median30 paired T4-A/T8-A; per rep geomean3 dev points; geomean10 aggregate reps',interval='20000 bootstrap resamples of 10 process aggregate log ratios; seed20261029; conditional single-session exploratory 95%',guard='max(exp(q95(abs(log per-rep gm3 T4-A/T4-B))),exp(q95(abs(log per-rep gm3 T8-A/T8-B))),1)',selection='Select8/4 iff primary bootstrap lower>1, geomean>aggregate guard, >=8/10 aggregate ratios>1, alternate T4-B/T8-B aggregate geomean>1, and no clear dev regression. Else retain4/2 and skip eval.',clear_regression='Any dev point: bootstrap upper<1 AND geomean<1/point guard AND >=8/10 point ratios<1. Point guard uses max of both same-implementation null q95 absolute log ratios.',inferential_supplement='Two-sided exact binomial sign test (ties excluded) at process level; dev3 secondary Holm family, eval15 separate Holm family. Exploratory exchangeability across processes in one session; no matrix population inference. Does not alter selection.',correctness='B/-B initial full validation, padding and unowned rows zero, final validation; timed outputs not all copied back',fixed=dict(W=16,candidate_budget=256,knn=16,long_row_split=False,full_output=True,skip_selection=False),profile='Separate event/API processes and frozen G/ST branches; branch scopes owned rows only, empty scope flagged; no sum/max overlap inference',eval_label='Frozen-config evaluation on previously seen matrices, not unseen test set',stop_after='D2 only: recover, independently audit, save, verified poweroff; no D3')

def freeze():
    x=json.loads(json.dumps(protocol()));p=D/'protocol.json'
    if p.exists():assert read(p)==x
    else:save(p,x)

def probe():
    x=prior_probe()
    for p in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            a=p.read_bytes().decode(errors='replace').split('\0');pid=int(p.parent.name)
            if pid!=os.getpid() and Path(a[0]).name.startswith('rsh_runner_d2'):x['experiments'].append(dict(pid=pid,argv=a))
        except (OSError,ValueError):pass
    return x

def validate(x,warm,repeats,event=False,smoke=False,parent=False):
    args=PROFILE_ARGS if event or smoke else ARGS;count=len(args)
    assert x['correctness'] and x['warmups']==warm and x['repeats']==repeats and [r['variant'] for r in x['records']]==[Path(a).name for a in args]
    assert x['b_rotation']==2 and x['timer']=='resident_synchronized_full_call_us'
    if not parent:assert sorted(x['allocation_order'])==list(range(count)) and len(x['allocation_order'])==count and isinstance(x['allocation_seed'],int)
    for i,r in enumerate(x['records']):
        assert r['native_clear'] and len(r['samples_us'])==repeats and all(math.isfinite(v) and v>0 for v in r['samples_us']);assert math.isfinite(r['max_abs_error']) and r['max_abs_error']>=0
        if i<6:assert r['valid_rows']==r['m']
    for i,j in [(0,1),(2,3)]:
        for k in ['m','k','n','cube_groups','k16_tiles','aiv_rows','valid_rows','max_abs_error']:assert x['records'][i][k]==x['records'][j][k]
    tr=x['trace'];assert len(tr)==count*(warm+repeats);previous=0
    for iswarm,length in [(True,warm),(False,repeats)]:
        for i in range(length):
            sub=[t for t in tr if t['warm']==iswarm and t['iteration']==i];assert len(sub)==count and sorted(t['record_index'] for t in sub)==list(range(count));assert [t['position'] for t in sub]==list(range(count))
            for t in sub:
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

def verify_cases(scope):
    for p,h in read(D/(scope+'_case_manifest.json'))['files'].items():assert sha(ROOT/p)==h,p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['freeze','prepare','measure','profile','finish'],required=True);ap.add_argument('--scope',choices=['dev','eval'],default='dev');a=ap.parse_args();D.mkdir(exist_ok=True)
    lock=(D/'controller.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);freeze()
    if a.phase=='freeze':print('D2_PROTOCOL_FROZEN',sha(D/'protocol.json'));return
    state=read(D/'progress.json') if (D/'progress.json').exists() else dict(state='initial',dev_completed=[],dev_profile_completed=[],eval_completed=[],eval_profile_completed=[],smoke=[])
    def stage(s):state['stage']=s;save(D/'progress.json',state);print(s,flush=True)
    def run(root,out,cores,warm,repeats,seed,event=False,smoke=False,parent=False):
        if out.exists():validate(read(out),warm,repeats,event,smoke,parent);return
        info=read(D/'build.json')['programs']['profile' if event else 'formal'];exe=ROOT/info['path']
        if parent:exe=ROOT/'build_d1b/rsh_runner_d1b_formal';assert sha(exe)=='d69d1782c84f6a0967145fe75a6c03fe8467c4d09fb43ecaaea64f22d63b4421'
        else:assert sha(exe)==info['sha256']
        out.parent.mkdir(parents=True,exist_ok=True);pending=out.with_name(out.stem+'.pending-'+str(time.time_ns())+'.json');env=probe();assert not env['experiments'],env['experiments'];save(out.with_suffix('.before.json'),env)
        args=PROFILE_ARGS if event or smoke else ARGS;cmd=[str(exe),str(root),str(cores),str(warm),str(repeats),str(seed),str(pending),*args];start=time.monotonic_ns();p=subprocess.run(cmd,capture_output=True,text=True,timeout=300);end=time.monotonic_ns();pending.with_suffix('.log').write_text(p.stdout+p.stderr);save(out.with_suffix('.after.json'),probe());save(out.with_suffix('.process.json'),dict(argv=cmd,exit=p.returncode,event=event,parent_program=parent,start_monotonic_ns=start,end_monotonic_ns=end))
        assert p.returncode==0,(pending,p.stderr[-3000:]);x=read(pending);validate(x,warm,repeats,event,smoke,parent)
        if not parent:assert x['allocation_seed']==(seed^0x5A17B39D)
        pending.replace(out);pending.with_suffix('.log').replace(out.with_suffix('.log'))
    if state['state']=='complete':print('D2_ALREADY_COMPLETE_STOP');return
    try:
        if a.scope=='eval':
            choice=read(D/'threshold_selection.json');assert choice['selected_thresholds']==[8,4] and choice['protocol_sha256']==sha(D/'protocol.json')
        if a.phase=='prepare':
            stage('D2_'+a.scope.upper()+'_PREFLIGHT');save(D/(a.scope+'_preflight.json'),probe());env=read(D/(a.scope+'_preflight.json'));assert not env['experiments'] and env['machine']=='aarch64'
            prepare(a.scope)
            if a.scope=='dev':
                build();stage('D2_ZERO_GUARD_RECHECK');parent=read(ROOT/'results/d1b/build.json')['executables']['zero_probe'];assert sha(ROOT/parent['path'])==parent['sha256'];p=subprocess.run([str(ROOT/parent['path']),str(D/'zero_probe.json')],capture_output=True,text=True,timeout=300);(D/'zero_probe.log').write_text(p.stdout+p.stderr);assert p.returncode==0 and read(D/'zero_probe.json')['tests']==40
                stage('D2_DEVICE_SMOKE')
                for root in read(D/'dev_case_manifest.json')['roots']:
                    if not Path(root).parent.name.startswith('smoke_'):continue
                    for cores in [1,24]:
                        for label,event,parent in [('parent',False,True),('formal',False,False),('profile',True,False)]:
                            key=Path(root).parent.name+f'_C{cores}_'+label;run(ROOT/root,D/'smoke'/f'{key}.json',cores,1,2,SEED,event,True,parent)
                            if key not in state['smoke']:state['smoke'].append(key)
                            save(D/'progress.json',state)
            state['state']=a.scope+'_prepared';stage('D2_'+state['state'].upper())
        elif a.phase in ['measure','profile']:
            assert len(state['smoke'])==24;verify_cases(a.scope);event=a.phase=='profile'
            source=[p for p in (ROOT/'diagnostics/d2').glob('*') if p.is_file()]+[ROOT/'scripts'/name for name in ['prepare_d2.py','run_d2.py','analyze_d2.py']]+[ROOT/'npu'/name for name in ['runner.cpp','dispatch.cpp','common.h','cube.cpp','vector.cpp','mix.cpp','restore.cpp','work.h']]
            frozen=dict(files={str(p.relative_to(ROOT)):sha(p) for p in source},protocol_sha256=sha(D/'protocol.json'),case_manifest_sha256=sha(D/(a.scope+'_case_manifest.json')),build_sha256=sha(D/'build.json'))
            mp=D/(a.scope+'_manifest.json')
            if mp.exists():assert read(mp)==frozen
            else:
                save(mp,frozen)
                for p in source:q=D/'source_snapshot'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
            formal=protocol()[a.scope+'_jobs'];jobs=protocol()[a.scope+'_profiles'] if event else formal
            if event:assert len(state[a.scope+'_completed'])==len(formal)
            state['state']=a.scope+('_profiling' if event else '_measuring');state.pop('error',None);stage('D2_'+state['state'].upper());field=a.scope+('_profile_completed' if event else '_completed');folder='profile' if event else 'measurements'
            for job in jobs:
                m,n,rep,seed=job['matrix'],job['n'],job['rep'],job['seed'];key=f'{m}/N{n}/run{rep}';run(ROOT/'cases_d2'/m/f'N{n}',D/a.scope/folder/m/f'N{n}'/f'run{rep}.json',24,10,30,seed,event)
                if key not in state[field]:state[field].append(key)
                save(D/'progress.json',state);print('D2_DONE',a.scope,folder,len(state[field]),'/',len(jobs),key,flush=True)
            state['state']=a.scope+('_profile_complete' if event else '_measurements_complete');stage('D2_'+state['state'].upper())
        else:
            assert len(state['dev_completed'])==30 and len(state['dev_profile_completed'])==9
            choice=read(D/'threshold_selection.json');selected=choice['selected_thresholds']==[8,4]
            if selected:assert len(state['eval_completed'])==150 and len(state['eval_profile_completed'])==45
            else:assert not state['eval_completed'] and not state['eval_profile_completed']
            for scope in ['dev']+(['eval'] if selected else []):
                verify_cases(scope)
                for event,key,folder in [(False,'_jobs','measurements'),(True,'_profiles','profile')]:
                    for j in protocol()[scope+key]:validate(read(D/scope/folder/j['matrix']/f'N{j["n"]}'/f'run{j["rep"]}.json'),10,30,event)
            save(D/'final_environment.json',probe());assert not read(D/'final_environment.json')['experiments'];state.update(state='complete',stage='D2_COMPLETE_STOP_BEFORE_D3',shutdown_required=True,local_recovery_audit_required=True);save(D/'progress.json',state);print(state['stage'],flush=True)
    except BaseException:
        state['state']='failed';state['error']=traceback.format_exc();save(D/'progress.json',state);raise
if __name__=='__main__':main()
