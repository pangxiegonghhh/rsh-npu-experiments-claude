"""Independent raw pair, cost, program and layout audit; no device execution."""
from pathlib import Path
import argparse,math,statistics,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1b import POINTS,ARGS,LABELS,sha,read,save
from scripts.run_d1b import validate
D=ROOT/'results/d1b'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full-inputs',action='store_true');a=ap.parse_args();state=read(D/'progress.json');assert state['state']=='complete' and len(set(state['completed']))==50 and len(set(state['profile_completed']))==15
    mf=read(D/'manifest.json')
    for k,name in [('protocol_sha256','protocol.json'),('case_manifest_sha256','case_manifest.json'),('build_sha256','build.json')]:assert sha(D/name)==mf[k]
    for p,h in mf['files'].items():assert sha(ROOT/p)==h and sha(D/'source_snapshot'/p)==h
    b=read(D/'build.json');assert not b['spmm_kernel_recompiled'] and b['new_clear_kernel_compiled']
    for name,e in b['executables'].items():assert sha(D/'device_binary'/Path(e['path']).name)==e['sha256']
    for name,e in read(D/'build_objects/index.json').items():assert sha(ROOT/e['saved'])==e['sha256']
    assert read(D/'zero_probe.json')['passed'] and read(D/'zero_probe.json')['tests']==40
    data=read(D/'local_audit.json');assert data['passed'];contrasts=[('Old-V0/New-V0',0,1),('Old-V2/New-V2',2,3),('Old-V2-Z/New-V2-Z',4,5),('Old-HV/New-HV-A',6,7),('Old-HV/New-HV-B',6,8),('New-V0/New-HV-A',1,7),('New-V2/New-HV-A',3,7),('New-V2-Z/New-HV-A',5,7),('New-V2/New-V2-Z',3,5),('New-HV-A/New-HV-B',7,8)]
    for p,h in data['source_sha256'].items():assert sha(ROOT/p)==h
    pairs=0;cost_checks=0;calls=0;mx=0.
    for m,n in POINTS:
        row=next(r for r in data['rows'] if r['matrix']==m and r['n']==n)
        for rep in range(10):
            x=read(D/'measurements'/m/f'N{n}'/f'run{rep}.json');validate(x,10,30);calls+=len(x['trace']);mx=max(mx,max(r['max_abs_error'] for r in x['records']))
            for k,i,j in contrasts:
                v=statistics.median(t/u for t,u in zip(x['records'][i]['samples_us'],x['records'][j]['samples_us']));assert math.isclose(v,row['contrasts'][k]['process_ratios'][rep],rel_tol=1e-12);pairs+=1
        for k,c in row['contrasts'].items():assert math.isclose(math.exp(statistics.mean(map(math.log,c['process_ratios']))),c['geomean'],rel_tol=1e-12)
        for rep in range(3):
            x=read(D/'profile'/m/f'N{n}'/f'run{rep}.json');validate(x,10,30,True);calls+=len(x['trace'])
            for i,l in enumerate(LABELS):
                c=next(t for t in row['costs'] if t['label']==l)
                for key,values in [('event_process_medians_us',x['events'][i]),('api_process_medians_us',x['host_api_us'][i])]:
                    for j in range(len(values[0])):assert statistics.median(t[j] for t in values)==c[key][rep][j];cost_checks+=1
    files=0;metadata=0
    for p,h in read(D/'case_manifest.json')['files'].items():
        if p.endswith('.bin'):
            if a.full_inputs:assert sha(ROOT/p)==h;files+=1
        else:assert sha(ROOT/p)==h;metadata+=1
    smoke=0
    for p in (D/'smoke').glob('*.json'):
        if p.name.endswith(('.before.json','.after.json','.process.json')):continue
        validate(read(p),1,2,p.stem.endswith('_profile'),True,not p.stem.endswith('_d0control'));smoke+=1
    assert (pairs,cost_checks,calls,smoke)==(500,2025,23400,24);assert not read(D/'final_environment.json')['experiments']
    result={'passed':True,'formal_processes':50,'formal_samples':13500,'profile_processes':15,'profile_samples':4050,'trace_calls':calls,'smoke_processes':smoke,'smoke_record_checks':smoke*13,'zero_guard_tests':40,'independent_process_ratios_checked':pairs,'independent_cost_process_medians_checked':cost_checks,'binary_files_checked':files,'metadata_flag_files_checked':metadata,'max_abs_error':mx,'spmm_kernels_recompiled':False,'clear_deleted_or_fused':False,'next':'D1b stop; recover/audit/save then power off; D2 not run'};save(D/'independent_audit.json',result);print(result)
if __name__=='__main__':main()
