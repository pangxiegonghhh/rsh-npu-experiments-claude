"""D3 only, resumable L/F/J mechanism comparisons with frozen native runtime."""
from __future__ import annotations
import argparse,fcntl,json,math,random,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));D=ROOT/'results/d3'
from scripts.prepare_d3 import ARGS,LABELS,PROFILE_ARGS,PROFILE_LABELS,POINTS,prepare,sha,read,save
from scripts.run_d2 import probe,validate as unused
SEED=20261031

def protocol():
    def jobs(count,seed):
        x=[dict(matrix=m,n=n,rep=r,seed=seed+r) for r in range(count) for m,n in POINTS];random.Random(seed+71).shuffle(x);return x
    return dict(schema='d3-protocol-v1',points=POINTS,args=ARGS,labels=LABELS,profile_args=PROFILE_ARGS,profile_labels=PROFILE_LABELS,jobs=jobs(10,SEED),profiles=jobs(3,SEED+1000),warmups=10,repeats=30,cores=24,backend='exact D2 formal/profile executables; native AIV zero, both required full clears',thresholds=[8,4],threshold_selection_sha256=sha(ROOT/'results/d2/threshold_selection.json'),W=16,candidate_budget=256,knn=16,long_row_split=False,full_output=True,zero_policy='For L/F/J/O all original zero rows are excluded from grouping; original M output remains allocated and cleared. J0 is exact D2 historical policy reference.',tail_policy='All remaining <16 nonzero candidate rows sent to AIV. L/F have identical tail count but not necessarily same tail members/nnz; reported.',length_rule='S={r: 0<nnz[r]<=8}, ascending original row order, exactly identical for L/F',L='Select S first; rebuild CSR row subset of nnz>8 with original K, ascending original row IDs; same bounded shared-column/IDF/kNN/MSF/DFS/refine on subset; map local IDs back then window.',F='Use original whole-matrix global reorder; remove exact same S and all zero rows, window remaining rows.',J='Same global reorder, remove all zero rows before 8/4 window-dependent partition.',O='Same global nonzero order, fixed full windows without S selection, AIV tail.',J0='Exact historical D2 8/4 order/routing/layout at every N, zero behavior unchanged; same process full-output reference.',V2_Z='Exact V2 whole zero-K group removal, remaining group order/tiles unchanged, native clear, full output; diagnostic reference, different padded-tail behavior from L/F/J.',primary_contrasts=['L-A/F-A','F-A/J-A','L-A/J-A'],unit='per point/process median30 iteration-paired ratios; per rep geomean24 fixed points; geomean10 reps',interval='20000 bootstrap samples of 10 aggregate log process ratios seed20261031; single-session conditional exploratory interval',guard='max(exp(q95(abs(log same-implementation duplicate process ratios))) for L,F,J,1); aggregate null formed across24 points per rep first',descriptive_positive='CI lower>1, geomean>same-layer max3 null guard, >=8/10 positive, alternate B/B direction>1, non-identical execution layouts. Point rule is descriptive.',workflow_followup_signal='Aggregate descriptive positive, at least two distinct matrices with a point satisfying descriptive rule; report clear regressions separately. No implementation/threshold adaptation from results.',inferential='Exact two-sided process sign tests; three aggregate primary tests Holm3; all24x3 primary point tests Holm72. Other controls descriptive only. One device session exchangeability approximate, no hardware/dataset population inference.',interpretation='L/F changes candidate domain, column weights and sampling local IDs as well as when organization occurs. L/F tail members may differ. F/J changes selected S, grouping, tail and S order. No single-feature pure causal claim, no Neutron reproduction/novelty claim.',correctness='Initial B/-B and final full output/padding checks; timed outputs not copied each iteration; G/ST-only validates owned rows with others zero, empty masks labeled.',prep='local subset order frozen; remote fresh global/subset reorder must reproduce saved orders exactly, record versions/costs. CPU components and host device_prepare_us are not complete application E2E; no q amortization claim.',stop_after='D3 complete: recover, audit, record, verify poweroff; do not start next stage')

def freeze():
    x=json.loads(json.dumps(protocol()));p=D/'protocol.json'
    if p.exists():assert read(p)==x
    else:save(p,x)

def validate(x,warm,repeats,event=False,smoke=False):
    args=PROFILE_ARGS if event or smoke else ARGS;count=len(args)
    assert x['correctness'] and x['warmups']==warm and x['repeats']==repeats and [r['variant'] for r in x['records']]==[Path(a).name for a in args]
    assert x['b_rotation']==2 and x['timer']=='resident_synchronized_full_call_us';assert len(x['allocation_order'])==count and sorted(x['allocation_order'])==list(range(count))
    for i,r in enumerate(x['records']):
        assert r['native_clear'] and len(r['samples_us'])==repeats and all(math.isfinite(v) and v>0 for v in r['samples_us']) and math.isfinite(r['max_abs_error']) and r['max_abs_error']>=0
        if i<9:assert r['valid_rows']==r['m']
    for i,j in [(0,1),(2,3),(4,5)]:
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
            for e,h,w in zip(x['events'][i],x['host_api_us'][i],x['records'][i]['samples_us']):assert len(e)==5 and len(h)==10 and all(math.isfinite(v) and v>=0 for v in e+h) and e[-1]>0 and abs(sum(e[:4])-e[4])<.03+1e-4*e[4] and sum(h)<=w+.1
    else:assert 'events' not in x

def reuse():
    p=read(ROOT/'results/d2/build.json');programs={}
    for label,e in p['programs'].items():
        q=ROOT/e['path'];assert sha(q)==e['sha256'];saved=D/'device_binary'/q.name;saved.parent.mkdir(exist_ok=True);shutil.copy2(q,saved);programs[label]=e
    idx=read(ROOT/'results/d2/build_objects/index.json');out={}
    for name,e in idx.items():
        src=ROOT/name;assert sha(src)==e['sha256'];q=D/'build_objects'/Path(e['saved']).name;q.parent.mkdir(exist_ok=True);shutil.copy2(src,q);out[name]=dict(saved=str(q.relative_to(ROOT)),sha256=e['sha256'])
    save(D/'build_objects/index.json',out);save(D/'build.json',dict(programs=programs,host_recompiled=False,kernel_recompiled=False,parent_d2_build_sha256=sha(ROOT/'results/d2/build.json'),parent_backend_sha256=sha(ROOT/'results/d1b/backend_selection.json'),reused_objects_sha256={k:e['sha256'] for k,e in out.items()}))

def verify_cases():
    for p,h in read(D/'case_manifest.json')['files'].items():assert sha(ROOT/p)==h,p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--phase',choices=['freeze','prepare','measure','profile','finish'],required=True);a=ap.parse_args();D.mkdir(exist_ok=True);lock=(D/'controller.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);freeze()
    if a.phase=='freeze':print('D3_PROTOCOL_FROZEN',sha(D/'protocol.json'));return
    state=read(D/'progress.json') if (D/'progress.json').exists() else dict(state='initial',completed=[],profile_completed=[],smoke=[])
    def stage(s):state['stage']=s;save(D/'progress.json',state);print(s,flush=True)
    def run(root,out,cores,warm,repeats,seed,event=False,smoke=False):
        if out.exists():validate(read(out),warm,repeats,event,smoke);return
        info=read(D/'build.json')['programs']['profile' if event else 'formal'];exe=ROOT/info['path'];assert sha(exe)==info['sha256'];out.parent.mkdir(parents=True,exist_ok=True);pending=out.with_name(out.stem+'.pending-'+str(time.time_ns())+'.json');env=probe();assert not env['experiments'];save(out.with_suffix('.before.json'),env)
        args=PROFILE_ARGS if event or smoke else ARGS;cmd=[str(exe),str(root),str(cores),str(warm),str(repeats),str(seed),str(pending),*args];start=time.monotonic_ns();p=subprocess.run(cmd,capture_output=True,text=True,timeout=600);end=time.monotonic_ns();pending.with_suffix('.log').write_text(p.stdout+p.stderr);save(out.with_suffix('.after.json'),probe());save(out.with_suffix('.process.json'),dict(argv=cmd,exit=p.returncode,event=event,start_monotonic_ns=start,end_monotonic_ns=end));assert p.returncode==0,(str(pending),p.stderr[-3000:]);x=read(pending);validate(x,warm,repeats,event,smoke);assert x['allocation_seed']==(seed^0x5A17B39D);pending.replace(out);pending.with_suffix('.log').replace(out.with_suffix('.log'))
    if state['state']=='complete':print('D3_ALREADY_COMPLETE_STOP');return
    try:
        if a.phase=='prepare':
            stage('D3_PREFLIGHT');save(D/'preflight.json',probe());env=read(D/'preflight.json');assert not env['experiments'] and env['machine']=='aarch64'
            stage('D3_CPU_REPRODUCTION_AND_COST');prepare(retime=True);reuse();verify_cases();stage('D3_ZERO_GUARD');e=read(ROOT/'results/d1b/build.json')['executables']['zero_probe'];assert sha(ROOT/e['path'])==e['sha256'];p=subprocess.run([str(ROOT/e['path']),str(D/'zero_probe.json')],capture_output=True,text=True,timeout=300);(D/'zero_probe.log').write_text(p.stdout+p.stderr);assert p.returncode==0 and read(D/'zero_probe.json')['tests']==40
            stage('D3_DEVICE_SMOKE')
            for root in read(D/'case_manifest.json')['roots']:
                if not Path(root).parent.name.startswith('smoke_'):continue
                for cores in [1,24]:
                    for label,event in [('formal',False),('profile',True)]:
                        key=Path(root).parent.name+f'_C{cores}_'+label;run(ROOT/root,D/'smoke'/f'{key}.json',cores,1,2,SEED,event,True)
                        if key not in state['smoke']:state['smoke'].append(key)
                        save(D/'progress.json',state)
            assert len(state['smoke'])==20;state['state']='prepared';stage('D3_PREPARED')
        elif a.phase in ['measure','profile']:
            assert len(state['smoke'])==20;verify_cases();event=a.phase=='profile';source=[ROOT/p for p in ['scripts/prepare_d3.py','scripts/run_d3.py','scripts/analyze_d3.py','scripts/prepare_d2.py','scripts/prepare_d1.py','scripts/hv_cases.py','rsh/planner.py','rsh/prepare.py']]+[ROOT/'diagnostics/d2'/n for n in ['runner.cpp','profile_runner.cpp']]+[ROOT/'npu'/n for n in ['runner.cpp','dispatch.cpp','common.h','cube.cpp','vector.cpp','mix.cpp','restore.cpp','work.h']];frozen=dict(files={str(p.relative_to(ROOT)):sha(p) for p in source},protocol_sha256=sha(D/'protocol.json'),case_manifest_sha256=sha(D/'case_manifest.json'),build_sha256=sha(D/'build.json'))
            if (D/'manifest.json').exists():assert read(D/'manifest.json')==frozen
            else:
                save(D/'manifest.json',frozen)
                for p in source:q=D/'source_snapshot'/p.relative_to(ROOT);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
            if event:assert len(state['completed'])==240
            state['state']='profiling' if event else 'measuring';state.pop('error',None);stage('D3_'+state['state'].upper());key='profile_completed' if event else 'completed';folder='profile' if event else 'measurements';jobs=protocol()['profiles' if event else 'jobs']
            for j in jobs:
                m,n,rep,seed=j['matrix'],j['n'],j['rep'],j['seed'];tag=f'{m}/N{n}/run{rep}';run(ROOT/'cases_d3'/m/f'N{n}',D/folder/m/f'N{n}'/f'run{rep}.json',24,10,30,seed,event)
                if tag not in state[key]:state[key].append(tag)
                save(D/'progress.json',state);print('D3_DONE',folder,len(state[key]),'/',len(jobs),tag,flush=True)
                if not event and len(state[key])==120:
                    with (D/'checkpoint-controller.log').open('a') as f:cp=subprocess.run([sys.executable,str(ROOT/'scripts/checkpoint_d3.py')],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=180)
                    assert cp.returncode==0;print('D3_MIDPOINT_CHECKPOINT_SAVED_NO_NPU_OVERLAP',flush=True)
            state['state']='profile_complete' if event else 'measurements_complete';stage('D3_'+state['state'].upper())
        else:
            assert len(state['completed'])==240 and len(state['profile_completed'])==72
            for event,folder,key in [(False,'measurements','jobs'),(True,'profile','profiles')]:
                for j in protocol()[key]:validate(read(D/folder/j['matrix']/f'N{j["n"]}'/f'run{j["rep"]}.json'),10,30,event)
            verify_cases();save(D/'final_environment.json',probe());assert not read(D/'final_environment.json')['experiments'];state.update(state='complete',stage='D3_COMPLETE_STOP',shutdown_required=True,local_recovery_audit_required=True);save(D/'progress.json',state);print(state['stage'],flush=True)
    except BaseException:
        state['state']='failed';state['error']=traceback.format_exc();save(D/'progress.json',state);raise
if __name__=='__main__':main()
