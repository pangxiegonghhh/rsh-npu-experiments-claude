"""Independent D2 raw, manifest, allocation, decision and input verification; CPU only."""
from pathlib import Path
import argparse,math,statistics,sys,random
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d2 import DEV,EVAL,LABELS,PROFILE_LABELS,sha,read,save
from scripts.run_d2 import validate,protocol
D=ROOT/'results/d2'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full-inputs',action='store_true');a=ap.parse_args();state=read(D/'progress.json');assert state['state']=='complete';choice=read(D/'threshold_selection.json');assert choice['protocol_sha256']==sha(D/'protocol.json') and choice['dev_analysis_sha256']==sha(D/'dev_analysis.json') and choice['backend_selection_sha256']==sha(ROOT/'results/d1b/backend_selection.json')
    assert choice['selected_thresholds']==([8,4] if all(choice['conditions'].values()) else [4,2]);scopes=['dev']+(['eval'] if choice['eval_allowed'] else [])
    b=read(D/'build.json');assert not b['kernel_recompiled'] and b['timed_device_calls_unchanged']
    for name,e in b['programs'].items():assert sha(D/'device_binary'/Path(e['path']).name)==e['sha256']
    for name,e in read(D/'build_objects/index.json').items():assert sha(ROOT/e['saved'])==e['sha256']==b['spmm_and_zero_objects_sha256'][name]
    assert read(D/'zero_probe.json')['passed'] and read(D/'zero_probe.json')['tests']==40
    pairs=costs=calls=files=metadata=formal=profiles=0;mx=0.;nullspreads=[]
    contrasts=[('T4-A/T8-A',0,2),('T4-B/T8-B',1,3),('T4-A/T8-B',0,3),('T4-B/T8-A',1,2),('T4-A/T4-B',0,1),('T8-A/T8-B',2,3),('V0/T4-A',4,0),('V0/T8-A',4,2),('V2/T4-A',5,0),('V2/T8-A',5,2)]
    for scope in scopes:
        mf=read(D/(scope+'_manifest.json'))
        for key,name in [('protocol_sha256','protocol.json'),('case_manifest_sha256',scope+'_case_manifest.json'),('build_sha256','build.json')]:assert sha(D/name)==mf[key]
        for p,h in mf['files'].items():assert sha(ROOT/p)==h and sha(D/'source_snapshot'/p)==h
        data=read(D/(scope+'_analysis.json'));assert data['passed']
        for p,h in data['source_sha256'].items():assert sha(ROOT/p)==h
        points=[(m,64) for m in DEV] if scope=='dev' else [(m,n) for m in EVAL for n in [16,64,256]]
        for m,n in points:
            row=next(r for r in data['rows'] if r['matrix']==m and r['n']==n)
            for rep in range(10):
                p=D/scope/'measurements'/m/f'N{n}'/f'run{rep}.json';x=read(p);validate(x,10,30);formal+=1;calls+=len(x['trace']);mx=max(mx,max(r['max_abs_error'] for r in x['records']));job=next(j for j in protocol()[scope+'_jobs'] if (j['matrix'],j['n'],j['rep'])==(m,n,rep));assert x['allocation_seed']==(job['seed']^0x5A17B39D)
                for key,i,j in contrasts:
                    v=statistics.median(t/u for t,u in zip(x['records'][i]['samples_us'],x['records'][j]['samples_us']));assert math.isclose(v,row['contrasts'][key]['process_ratios'][rep],rel_tol=1e-12);pairs+=1
                for suffix in ['before','after']:
                    env=read(p.with_suffix('.'+suffix+'.json'));assert not env['experiments'] and env['machine']=='aarch64'
                proc=read(p.with_suffix('.process.json'));assert proc['exit']==0 and not proc['event'] and not proc['parent_program'] and proc['argv'][0].endswith('rsh_runner_d2_formal')
            for key,c in row['contrasts'].items():assert math.isclose(math.exp(statistics.mean(map(math.log,c['process_ratios']))),c['geomean'],rel_tol=1e-12)
            for rep in range(3):
                x=read(D/scope/'profile'/m/f'N{n}'/f'run{rep}.json');validate(x,10,30,True);profiles+=1;calls+=len(x['trace'])
                for i,l in enumerate(PROFILE_LABELS):
                    c=next(t for t in row['costs'] if t['label']==l)
                    for key,values in [('event_process_medians_us',x['events'][i]),('api_process_medians_us',x['host_api_us'][i])]:
                        for j in range(len(values[0])):assert statistics.median(t[j] for t in values)==c[key][rep][j];costs+=1
        for key,i,j in contrasts:
            for rep in range(10):
                value=math.exp(statistics.mean(math.log(r['contrasts'][key]['process_ratios'][rep]) for r in data['rows']));assert math.isclose(value,data['aggregate'][key]['process_ratios'][rep],rel_tol=1e-12)
        if a.full_inputs:
            import numpy as np
            for root in read(D/(scope+'_case_manifest.json'))['roots']:
                for tag in ['t4','t8']:
                    base=ROOT/root/tag;cfg=list(map(int,(base/'H-V/config.txt').read_text().split()));m=cfg[0];matrix=Path(root).parent.name;routing=read(D/'plans'/tag/matrix/'routing.json')['split'];expectedg=np.array([r for group in routing['groups'] for r in group],np.int32);expecteds=np.array(routing['residual']+routing['tail'],np.int32)
                    actualg=np.fromfile(base/'H-V/rowmap.bin',np.int32);actuals=np.fromfile(base/'H-V/srows.bin',np.int32);assert np.array_equal(actualg,expectedg) and np.array_equal(actuals,expecteds);assert cfg[5]==len(routing['groups']) and cfg[7]==len(expecteds)
                    vg=np.zeros(m,np.uint8);vs=vg.copy();vg[expectedg]=1;vs[expecteds]=1
                    assert not np.any(vg&vs) and np.all(np.fromfile(base/'H-V/valid.bin',np.uint8)==1)
                    assert np.array_equal(vg,np.fromfile(base/'G-only/V2/valid.bin',np.uint8)) and np.array_equal(vs,np.fromfile(base/'ST-only/V0/valid.bin',np.uint8))
                    for partial in ['G-only/V2','ST-only/V0']:
                        for key in ['ptr','cols','values','rhs','golden']:assert sha(base/partial/(key+'.bin'))==sha(base/'H-V'/(key+'.bin'))
        for p,h in read(D/(scope+'_case_manifest.json'))['files'].items():
            if p.endswith('.bin'):
                if a.full_inputs:assert sha(ROOT/p)==h;files+=1
            else:assert sha(ROOT/p)==h;metadata+=1
    def independent_q(values,q):
        z=sorted(values);k=(len(z)-1)*q;lo=int(k);hi=min(lo+1,len(z)-1);return z[lo]+(z[hi]-z[lo])*(k-lo)
    data=read(D/'dev_analysis.json');c=data['aggregate']['T4-A/T8-A'];v=c['process_ratios'];rng=random.Random(20261029);logs=list(map(math.log,v));draws=[math.exp(sum(logs[rng.randrange(10)] for _ in range(10))/10) for _ in range(20000)];ci=[independent_q(draws,.025),independent_q(draws,.975)]
    assert all(math.isclose(x,y,rel_tol=1e-12) for x,y in zip(ci,c['bootstrap95_conditional']))
    expected_guard=max(1.,*[math.exp(independent_q([abs(math.log(x)) for x in data['aggregate'][k]['process_ratios']],.95)) for k in ['T4-A/T4-B','T8-A/T8-B']]);assert math.isclose(expected_guard,data['aggregate_null_guard'],rel_tol=1e-12)
    conditions=dict(primary_ci_lower_above_one=c['bootstrap95_conditional'][0]>1,primary_exceeds_guard=c['geomean']>data['aggregate_null_guard'],at_least_eight_process_aggregates_faster=c['faster_count']>=8,alternate_copies_direction=data['aggregate']['T4-B/T8-B']['geomean']>1,no_clear_dev_regression=not any(r['clear_dev_regression'] for r in data['rows']));assert choice['conditions']==conditions
    smoke=0
    for p in (D/'smoke').glob('*.json'):
        if p.name.endswith(('.before.json','.after.json','.process.json')):continue
        validate(read(p),1,2,p.stem.endswith('_profile'),True,p.stem.endswith('_parent'));smoke+=1
    assert smoke==24 and formal==(180 if choice['eval_allowed'] else 30) and profiles==(54 if choice['eval_allowed'] else 9)
    assert not read(D/'final_environment.json')['experiments'];result=dict(passed=True,scopes=scopes,formal_processes=formal,formal_samples=formal*180,profile_processes=profiles,profile_samples=profiles*300,trace_calls=calls,smoke_processes=smoke,smoke_record_checks=240,zero_guard_tests=40,independent_process_ratios_checked=pairs,independent_cost_process_medians_checked=costs,binary_files_checked=files,metadata_flag_files_checked=metadata,max_abs_error=mx,selected_thresholds=choice['selected_thresholds'],next='D2 stop; recover/save then verified poweroff; no D3');save(D/'independent_audit.json',result);print(result)
if __name__=='__main__':main()
