"""Collect closed E0 runs; uses only stdlib and does not launch device work."""
from pathlib import Path
import csv
import hashlib
import json
import tarfile
import time

p=Path('/data/e0-supplement-r1')

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect() -> dict:
    assert (p/'final.rc').read_text().strip()=='FINAL_RC=0'
    summary=json.loads((p/'summary-final.json').read_text())
    normal=json.loads((p/'results/normal-final/checks.json').read_text())
    final=json.loads((p/'checks-final.json').read_text())
    assert len(normal)==223 and all(x['status']=='PASS' for x in normal)
    assert len(final)==27 and all(x['status']=='PASS' for x in final)
    assert sum(x['iterations'] for x in final)==216
    checkpoint=json.loads((p/'manifest-checkpoint.json').read_text())
    for name,value in {**checkpoint['source_sha256'],**checkpoint['binary_sha256']}.items():
        assert digest(p/name)==value,('changed since checkpoint',name)
    for path in p.glob('results/final-poison-*/*/host.json'):
        metadata=json.loads(path.read_text());assert metadata['guard_byte']==54
        raw=(path.parent/'output-0.bin').read_bytes();assert raw[:1024]==bytes([54])*1024 and raw[-1024:]==bytes([54])*1024
    poison=list(p.glob('results/final-poison-*/*/host.json'));assert len(poison)==6
    for mode in ['normal','direct']:
        obj=json.loads((p/f'results/integrated-{mode}-final/results.json').read_text())
        assert obj['correctness'] and obj['e0_guarded'] and len(obj['records'])==17
    for rep in range(3):
        obj=json.loads((p/f'results/final-integrated-repeat-{rep}/results.json').read_text())
        assert obj['correctness'] and obj['e0_guarded'] and len(obj['records'])==2
    resource={}
    for line in (p/'resources.txt').read_text().splitlines():
        words=line.split()
        if len(words)==2 and all(x.isdigit() for x in words):resource[int(words[0])]=int(words[1])
    names={3:'L1',0:'L0A',1:'L0B',2:'L0C',5:'UB'}
    assert set(resource)==set(names)
    (p/'resources.json').write_text(json.dumps({'soc':'Ascend910B2','method':'PlatformAscendC::GetCoreMemSize','bytes':{names[k]:v for k,v in resource.items()},'raw':'resources.txt'},indent=2)+'\n')
    cases=json.loads((p/'inputs/manifest.json').read_text())['cases']
    specs={x['id']:x for x in cases}
    for case in cases:
        for name,value in case['sha256'].items():assert digest(p/'inputs'/case['id']/name)==value
    with (p/'results-final.csv').open('w') as handle:
        writer=csv.writer(handle);writer.writerow(['case_id','stage','M','K','N','Mp','Kp','Np','status','max_abs_error','guard_errors','observation'])
        for x in normal:
            c=specs[x['case_id']]['config'];guards=sum(q['guard_errors']+q['debug_guard_errors'] for q in x['checks'])+sum(q['guard_errors'] for q in x['sources'].values())
            writer.writerow([x['case_id'],x['stage'],*c[:6],x['status'],x['max_abs_error'],guards,x['observation_method']])
    sdk=Path('/usr/local/Ascend/cann-9.0.0')
    header_names={'kernel_operator.h','kernel_struct_mm.h','kernel_struct_data_copy.h','platform_ascendc.h','platform_info.h'}
    headers={str(x.resolve()):digest(x) for x in sdk.rglob('*.h') if x.name in header_names and x.is_file()}
    assert header_names.issubset({Path(x).name for x in headers}),('missing SDK header hashes',headers)
    (p/'sdk-header-hashes.json').write_text(json.dumps(headers,indent=2)+'\n')
    history=p/'source-history';history.mkdir(exist_ok=True)
    for name in ['e0-supplement-r1.tar.gz','e0-integrated-r1.tar.gz','e0-split-r2.tar.gz','e0-extra-r3.tar.gz','e0-rotation-r4.tar.gz','e0-finish-r5.tar.gz','e0-sync-r6.tar.gz','e0-clean-r8.tar.gz']:
        src=p.parent/name
        assert src.exists(),name
        (history/name).write_bytes(src.read_bytes())
    files=set()
    for folder in ['npu','scripts','rsh','results','inputs','integrated-inputs','invalid-inputs','source-history']:
        files.update(x for x in (p/folder).rglob('*') if x.is_file() and '__pycache__' not in str(x))
    for pattern in ['*.log','*.json','*.txt','*.sh','*.rc','*.cpp','*.csv','collect_evidence.py']:
        files.update(x for x in p.glob(pattern) if x.is_file())
    for folder in ['build-final','integrated-final']:
        files.add(p/folder/'CMakeCache.txt')
        files.update((p/folder).glob('CMakeFiles/*_host_stub_obj.dir/auto_gen/*/host_stub.cpp'))
        files.update((p/folder).rglob('compile_commands.json'))
    file_hashes={str(x.relative_to(p)):digest(x) for x in sorted(files)}
    (p/'evidence-files-sha256.json').write_text(json.dumps(file_hashes,indent=2)+'\n')
    files.add(p/'evidence-files-sha256.json')
    archive=p/'e0-evidence-final.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for x in sorted(files):tar.add(x,arcname=str(x.relative_to(p)),recursive=False)
    info={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':digest(archive),'file_count':len(files),'collected_unix':time.time(),'normal_cases':223,'repeat_probe_runs':27,'repeat_probe_calls':216,'poison_patterns_verified':6,'headers_hashed':len(headers)}
    (p/'transfer-info.json').write_text(json.dumps(info,indent=2)+'\n')
    return info

if __name__=='__main__':print(json.dumps(collect()))
