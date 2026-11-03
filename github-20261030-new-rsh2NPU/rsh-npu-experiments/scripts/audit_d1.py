"""Independent provenance/ownership/raw-statistic audit; no device execution."""
from __future__ import annotations
import argparse,hashlib,json,math,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1 import POINTS,ARGS,LABELS,KEYS,read,sha,save
from scripts.run_d1 import validate
D=ROOT/'results/d1'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--full-inputs',action='store_true');args=ap.parse_args()
    state=read(D/'progress.json');assert state['state']=='complete' and len(set(state['completed']))==50 and len(set(state['profile_completed']))==15
    mf=read(D/'manifest.json')
    for k,p in [('protocol_sha256','protocol.json'),('case_manifest_sha256','case_manifest.json'),('build_sha256','build.json')]:assert sha(D/p)==mf[k]
    for p,h in mf['files'].items():assert sha(ROOT/p)==h and sha(D/'source_snapshot'/p)==h,p
    build=read(D/'build.json');assert not build['kernel_recompiled'];assert sha(D/'device_binary/rsh_runner_formal')==build['formal_executable_sha256'];assert sha(D/'device_binary/rsh_runner_profile')==build['event_executable_sha256']
    for p,e in read(D/'build_objects/index.json').items():assert sha(ROOT/e['saved'])==e['sha256']==build['reused_original_objects_sha256'][p]
    data=read(D/'local_audit.json');assert data['passed'];count=0;traces=0;ratios=0;mx=0.;binary=0
    for p,h in data['source_sha256'].items():assert sha(ROOT/p)==h
    for event,reps,folder in [(False,10,'measurements'),(True,3,'profile')]:
        for m,n in POINTS:
            row=next(r for r in data['rows'] if r['matrix']==m and r['n']==n)
            for rep in range(reps):
                p=D/folder/m/f'N{n}'/f'run{rep}.json';raw=read(p);validate(raw,10,30,event);count+=1;traces+=len(raw['trace']);mx=max(mx,max(r['max_abs_error'] for r in raw['records']));proc=read(p.with_suffix('.process.json'));assert proc['exit']==0 and proc['event']==event and proc['argv'][-7:]==ARGS
                if not event:
                    for name,i,j in [('V2/V2-Z',1,2),('V2-Z/HV-A',2,3),('V2/HV-A',1,3),('V0/HV-A',0,3),('V2/HV-B',1,4),('V2-Z/HV-B',2,4),('HV-A/HV-B',3,4)]:
                        ratio=statistics.median(a/b for a,b in zip(raw['records'][i]['samples_us'],raw['records'][j]['samples_us']));assert math.isclose(ratio,row['contrasts'][name]['process_ratios'][rep],rel_tol=1e-12);ratios+=1
            if not event:
                for c in row['contrasts'].values():assert math.isclose(math.exp(statistics.mean(map(math.log,c['process_ratios']))),c['geomean'],rel_tol=1e-12)
    metadata=0
    for p,h in read(D/'case_manifest.json')['files'].items():
        if p.endswith('.bin'):
            if args.full_inputs:assert sha(ROOT/p)==h;binary+=1
        else:assert sha(ROOT/p)==h;metadata+=1
    if args.full_inputs:
        import numpy as np
        for root in read(D/'case_manifest.json')['roots']:
            r=ROOT/root;v2=r/'V2';z=r/'V2-Z/V2';hv=r/'H-V';g=r/'G-only/V2';st=r/'ST-only/V0'
            gp=np.fromfile(v2/'cube_ptr.bin',np.int64);keep=np.diff(gp)>0;rm=np.fromfile(v2/'rowmap.bin',np.int32).reshape(-1,16)
            assert np.array_equal(np.fromfile(z/'rowmap.bin',np.int32),rm[keep].reshape(-1))
            assert np.array_equal(np.diff(np.fromfile(z/'cube_ptr.bin',np.int64)),np.diff(gp)[keep])
            for k in ['colref','tiles','ptr','cols','values','rhs','golden','valid']:assert sha(z/(k+'.bin'))==sha(v2/(k+'.bin'))
            for k in ['cube_ptr','rowmap','colref','tiles']:assert sha(g/(k+'.bin'))==sha(hv/(k+'.bin'))
            assert sha(st/'srows.bin')==sha(hv/'srows.bin')
            vg=np.fromfile(g/'valid.bin',np.uint8);vs=np.fromfile(st/'valid.bin',np.uint8);assert not np.any(vg&vs)
            ptr=np.fromfile(hv/'ptr.bin',np.int32);assert np.all((vg|vs)[np.diff(ptr)>0])
    smoke=0
    for p in (D/'smoke').glob('*.json'):
        if p.name.endswith(('.before.json','.after.json','.process.json')):continue
        validate(read(p),1,2,p.stem.endswith('_event'));smoke+=1
    assert (count,traces,ratios,smoke)==(65,18200,350,16);assert not read(D/'final_environment.json')['experiments']
    out={'passed':True,'formal_processes':50,'event_processes':15,'formal_samples':10500,'event_samples':3150,'trace_calls':traces,'smoke_processes':smoke,'smoke_record_checks':smoke*7,'paired_process_ratios_independently_checked':ratios,'case_metadata_files_checked':metadata,'binary_files_checked':binary,'max_abs_error':mx,'kernel_recompiled':False,'next':'stop after D1; verify backup then power off; D2 not run'};save(D/'independent_audit.json',out);print(json.dumps(out))
if __name__=='__main__':main()
