"""Independent D0 provenance, layout metadata, trace and paired-statistic audit."""
from __future__ import annotations
import argparse,hashlib,json,math,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.run_d0 import POINTS,validate
D=ROOT/'results/d0'
def read(p:Path)->dict:return json.loads(p.read_text())
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def actual_case(path:str)->Path:
    p=ROOT/path
    if p.exists():return p
    parts=Path(path).parts;v=parts[-1]
    if parts[0]=='cases_hv' and v in ['V0','V2']:return ROOT/('cases_'+v.lower())/parts[1]/parts[2]/v
    return p

def main()->None:
    ap=argparse.ArgumentParser();ap.add_argument('--full-inputs',action='store_true');args=ap.parse_args()
    state=read(D/'progress.json');assert state['state']=='complete' and len(set(state['completed']))==50
    mf=read(D/'manifest.json');assert sha(D/'protocol.json')==mf['protocol_sha256'];assert sha(D/'case_manifest.json')==mf['case_manifest_sha256'];assert sha(D/'build.json')==mf['build_sha256']
    for name,h in mf['files'].items():assert sha(ROOT/name)==h,name
    build=read(D/'build.json');assert build['kernel_recompiled'] is False
    for label,h in [('rsh_runner_original',mf['base_executable_sha256']),('rsh_runner_d0',mf['diagnostic_executable_sha256'])]:assert sha(D/'device_binary'/label)==h
    assert not any(name.endswith('/runner.cpp.o') for name in build['reused_original_objects_sha256'])
    for name,entry in read(D/'build_objects/index.json').items():assert sha(ROOT/entry['saved'])==entry['sha256']==build['reused_original_objects_sha256'][name]
    case_manifest=read(D/'case_manifest.json');meta_checks=0;binary_checks=0
    for name,h in case_manifest['files'].items():
        parent=actual_case(str(Path(name).parent));assert sha(parent/Path(name).name)==h;meta_checks+=1
    for name,hashes in case_manifest['binary_files'].items():
        p=actual_case(name);meta=read(p/'metadata.json');assert meta['files_sha256']==hashes
        if args.full_inputs:
            for key,h in hashes.items():assert sha(p/(key+'.bin'))==h;binary_checks+=1
    data=read(D/'local_audit.json');assert data['passed'] and data['independent_processes']==50
    sources=0
    for name,h in data['source_sha256'].items():assert sha(ROOT/name)==h;sources+=1
    trace_calls=0;sample_count=0;ratios_checked=0;smoke_count=0;max_error=0.
    for matrix,n in POINTS:
        row=next(r for r in data['rows'] if r['matrix']==matrix and r['n']==n)
        all_ratios={name:[] for name in ['V2/HV-A','V0/HV-A','V2/HV-B','V0/HV-B','HV-A/HV-B']}
        for rep in range(10):
            p=D/'measurements'/matrix/f'N{n}'/f'run{rep}.json';raw=read(p);validate(raw,10,30)
            assert raw['cores_aic_budget']==raw['cores_aic']==24 and raw['cores_aiv']==48
            for index,v in enumerate(['V0','V2','H-V','H-V']):
                cfg=[int(a) for a in (actual_case(f'cases_hv/{matrix}/N{n}/{v}')/'config.txt').read_text().split()]
                r=raw['records'][index];assert (r['m'],r['k'],r['n'],r['cube_groups'],r['k16_tiles'],r['aiv_rows'])==(cfg[0],cfg[1],cfg[2],cfg[5],cfg[6],cfg[7]);max_error=max(max_error,r['max_abs_error'])
            for name,a,b in [('V2/HV-A',1,2),('V0/HV-A',0,2),('V2/HV-B',1,3),('V0/HV-B',0,3),('HV-A/HV-B',2,3)]:
                ratio=statistics.median(x/y for x,y in zip(raw['records'][a]['samples_us'],raw['records'][b]['samples_us']))
                assert math.isclose(ratio,row['contrasts'][name]['process_ratios'][rep],rel_tol=1e-12);all_ratios[name].append(ratio);ratios_checked+=1
            process=read(p.with_suffix('.process.json'));assert process['exit']==0 and process['argv'][2:6]==['24','10','30',str(20261018+rep)]
            trace_calls+=len(raw['trace']);sample_count+=sum(len(r['samples_us']) for r in raw['records'])
        for name,ratios in all_ratios.items():assert math.isclose(math.exp(statistics.mean(math.log(x) for x in ratios)),row['contrasts'][name]['geomean'],rel_tol=1e-12)
    for p in (D/'smoke').glob('*.json'):
        if p.name.endswith(('.before.json','.after.json','.process.json')):continue
        validate(read(p),1,2,require_trace=p.stem.endswith('_trace'));smoke_count+=1
    assert (trace_calls,sample_count,smoke_count,ratios_checked)==(8000,6000,16,250)
    assert not read(D/'final_environment.json')['experiments']
    result={'passed':True,'formal_processes':50,'formal_samples':sample_count,'traced_calls':trace_calls,'smoke_processes':smoke_count,'smoke_record_checks':smoke_count*4,'same_layer_process_ratios_independently_checked':ratios_checked,'raw_source_sha256_checked':sources,'case_metadata_files_checked':meta_checks,'full_input_binary_files_checked':binary_checks,'max_abs_error':max_error,'kernel_recompiled':False,'new_host_executable':True,'next':'stop; D1 not run; poweroff after backup'}
    (D/'independent_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
