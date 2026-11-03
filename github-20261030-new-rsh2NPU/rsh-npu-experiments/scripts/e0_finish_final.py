"""Final E0 coverage/repeat/guard checks. Run inside the recorded device root."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from e0_supplement import validate, write_json

root=Path.cwd();base=root/'results';commands=[];records=[]

def execute(cmd: list[str], logfile: Path, env: dict[str,str] | None=None) -> subprocess.CompletedProcess:
    item={'argv':cmd,'env_overrides':env or {},'start':time.time()};commands.append(item)
    write_json(root/'commands-final.json',commands)
    proc=subprocess.run(cmd,env={**os.environ,**(env or {})},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
    logfile.parent.mkdir(parents=True,exist_ok=True);logfile.write_bytes(proc.stdout)
    item['returncode']=proc.returncode;item['end']=time.time();write_json(root/'commands-final.json',commands)
    return proc


def probe(case: str, mode: str, group: str, iterations: int=1, env: dict[str,str] | None=None) -> None:
    dst=base/group/case;dst.mkdir(parents=True,exist_ok=True)
    proc=execute([str(root/'build-final'/f'e0_{mode}'),str(root/'inputs'/case),str(dst),'direct' if mode=='direct' else 'normal',str(iterations)],dst/'run.log',env)
    if proc.returncode:raise RuntimeError((case,mode,proc.returncode,proc.stdout[-1000:]))
    result=validate(root/'inputs'/case,dst,mode=='direct');result['group']=group;records.append(result)
    write_json(root/'checks-final.json',records)
    print(group,case,result['status'],flush=True)
    if result['status']!='PASS':raise RuntimeError(result)


def main() -> None:
    initial=json.loads((base/'normal-final'/'checks.json').read_text())
    assert len(initial)==223 and all(x['status']=='PASS' for x in initial)
    for name,direct in [('split-normal-final',False),('split-direct-final',True),('dual-direct',True)]:
        result=validate(root/'inputs'/'control_K16_N16',base/name,direct)
        # Same-TU dual-direct is retained as a diagnostic, not an expected usable artifact.
        if name!='dual-direct':assert result['status']=='PASS',result
    for group in ('integrated-normal-final','integrated-direct-final'):
        result=json.loads((base/group/'results.json').read_text());assert result['correctness'] and result['e0_guarded'] and len(result['records'])==17
    # Host rejection happens before device initialization or submission.
    rejection=[]
    for kind in ('negative-ref','misaligned-shape'):
        dst=root/'invalid-inputs'/kind;shutil.copytree(root/'inputs'/'control_K16_N16',dst,dirs_exist_ok=True)
        import numpy as np
        if kind=='negative-ref':
            v=np.fromfile(dst/'refs.bin',dtype='<i4');v[0]=-1;v.tofile(dst/'refs.bin')
        else:
            v=np.fromfile(dst/'config.bin',dtype='<i4');v[3]=17;v.tofile(dst/'config.bin')
        proc=execute([str(root/'build-final'/'e0_normal'),str(dst),str(base/'final-rejection'/kind)],base/'final-rejection'/f'{kind}.log')
        assert proc.returncode!=0 and b'Unsafe' in proc.stdout
        rejection.append({'case':kind,'status':'EXPECTED_REJECT','returncode':proc.returncode,'message':proc.stdout.decode()})
    write_json(root/'host-rejection.json',rejection)
    cores=[('control_K16_N16','normal'),('control_K16_N16','direct'),('N-tail_K48_N33','normal'),
           ('B-selector_K48_N64_l0_b1_element_s2','normal'),('B-selector_K48_N64_l1_b1_element_s2','normal'),
           ('tail-B-selector_K37_s2','normal'),('logical_M30_K70_N40','normal')]
    for rep in range(3):
        for case,mode in cores:probe(case,mode,f'final-repeat-{rep}-{mode}',10)
    for case,mode in [('control_K17_N17','normal'),('compact-A-selector_v5','normal'),
                      ('tail-B-selector_K37_s2','normal'),('logical_M30_K70_N40','normal'),
                      ('mapping_segments','normal'),('control_K17_N17','direct')]:
        probe(case,mode,'final-poison-'+mode,1,{'E0_GUARD_BYTE':'0x36'})
    for rep in range(3):
        out=base/f'final-integrated-repeat-{rep}';out.mkdir(parents=True,exist_ok=True)
        cmd=[str(root/'integrated-final'/'rsh_guarded'),str(root/'integrated-inputs'),'1','1','10','20261021',str(out/'results.json'),'M30_K70_N40/V1','ADJACENT_U17_U37_N33/V1']
        p=execute(cmd,out/'run.log');assert p.returncode==0,p.stdout
        data=json.loads((out/'results.json').read_text());assert data['correctness'] and data['e0_guarded']
    # Preserve tool-generated metadata, binaries are identified by hash.
    hashes={}
    for basepath in (root/'npu',root/'scripts',root/'build-final',root/'integrated-final'):
        for p in basepath.rglob('*'):
            if not p.is_file() or '__pycache__' in str(p):continue
            if basepath.name in ('npu','scripts') or p.name.startswith(('e0_','rsh_')) and p.stat().st_mode & 0o111:
                hashes[str(p.relative_to(root))]=hashlib.sha256(p.read_bytes()).hexdigest()
    write_json(root/'source-binary-hashes.json',hashes)
    summary={'schema':'e0-supplement-summary-v1','normal_cases':len(initial),'extra_cases':0,
             'all_normal_pass':True,'normal_max_error':max(x['max_abs_error'] for x in initial),
             'final_probe_runs':len(records),'final_probe_calls':sum(x['iterations'] for x in records),
             'all_final_probes_pass':all(x['status']=='PASS' for x in records),
             'integrated_cases_per_path':17,'integrated_paths':['normal-final','direct-final'],
             'integrated_repeat_processes':3,'integrated_repeat_cases':['M30_K70_N40','ADJACENT_U17_U37_N33'],
             'known_failing_diagnostic':'same-translation-unit dual entry',
             'repaired_diagnostic':'separate translation units normal/direct entries',
             'end_unix':time.time()}
    write_json(root/'summary-final.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':main()
