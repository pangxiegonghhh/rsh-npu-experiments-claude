"""Only V1 is a new main version; V0 is its contemporaneous control.

No transition to V2. Every completed process is checkpointed atomically.
"""
from pathlib import Path
import hashlib
import json
import os
import random
import statistics
import subprocess
import sys
import time

import numpy as np
from scipy.sparse import csr_matrix

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rsh.planner import Matrix,layout,execute_cpu
from rsh.prepare import export


def digest(f: Path) -> str:
    return hashlib.sha256(f.read_bytes()).hexdigest()


def save(path: Path,value: dict) -> None:
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2));tmp.replace(path)


def main() -> None:
    dest=ROOT/'results/v1';dest.mkdir(exist_ok=True)
    exe=ROOT/'build_v4/rsh_runner'
    files=sorted((ROOT/'inputs').glob('*.npz'));assert len(files)==8
    manifest={'version':'V1','source_hashes':{str(f.relative_to(ROOT)):digest(f) for f in sorted((ROOT/'npu').glob('*')) if f.is_file()},
              'controller_sha256':digest(Path(__file__)),'executable_sha256':digest(exe),
              'inputs':{f.name:digest(f) for f in files},
              'protocol':{'new_main_version':'V1','control':'V0','w':16,'tail':'zero padded Cube',
                          'order':'original','aic_budget':24,'widths':[16,64,256],
                          'warmups':10,'samples':30,'processes':3,'seed':20261017,
                          'b_seed':'20261017+N','timing':'full synchronized resident call',
                          'dispatch':'separate Cube plus AIV output restoration; no mixed dispatch',
                          'stop_before':'V2'}}
    f=dest/'manifest.json'
    if f.exists():assert json.loads(f.read_text())==manifest,'Changed provenance: select a new result directory'
    else:save(f,manifest)
    status=dest/'progress.json'
    state=json.loads(status.read_text()) if status.exists() else {'version':'V1','state':'running','completed':[]}
    state['state']='running';save(status,state)

    def run(cmd: list[str],out: Path,timeout: int=300) -> dict:
        try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            state.update(state='failed',failed=str(out),error='process timeout');save(status,state)
            out.with_suffix('.log').write_text(str(exc));raise
        out.with_suffix('.log').write_text(r.stdout+r.stderr)
        if r.returncode:
            state.update(state='failed',failed=str(out),error=(r.stdout+r.stderr)[-3500:]);save(status,state)
            raise RuntimeError(r.stdout+r.stderr)
        result=json.loads(out.read_text());assert result['correctness']
        return result

    sm=dest/'smoke';sm.mkdir(exist_ok=True)
    for m in [7,16,17,32,65]:
        for n in [33,64]:
            for cores in [1,24]:
                out=sm/f'M{m}_N{n}_C{cores}.json'
                if out.exists() and json.loads(out.read_text()).get('correctness'):continue
                run([str(exe),str(ROOT/f'cases/smoke_M{m}/N{n}'),str(cores),'1','2','20261017',str(out),'V1'],out,90)
    print('V1_SMOKE_PASS 20/20',flush=True)

    for source in files:
        a=Matrix.load(str(source));order=np.arange(a.shape[0]);t=time.perf_counter()
        plan=layout(a,order,{'w':16,'tail':[]},'V1');layout_seconds=time.perf_counter()-t
        ref=csr_matrix((a.val.astype(np.float64),a.col,a.ptr),shape=a.shape)
        for n in [16,64,256]:
            base=ROOT/'cases_v0'/source.stem/f'N{n}'/'V0'
            baseline_meta=json.loads((base/'metadata.json').read_text())
            out=ROOT/'cases_v1'/source.stem/f'N{n}'/'V1'
            marker=out/'metadata.json'
            if not marker.exists():
                b=np.random.default_rng(20261017+n).uniform(-1,1,(a.shape[1],n)).astype(np.float16)
                golden=(ref@b.astype(np.float64)).astype(np.float32)
                export(a,plan,b,golden,out,{'matrix':source.stem,'input_sha256':digest(source),'n':n,
                       'b_seed':20261017+n,'order':'identity','w':16,'layout_seconds':layout_seconds,
                       'cube_groups':len(plan['cube_ptr'])-1,'k16_tiles':len(plan['tiles']),
                       'tail_rows':a.shape[0]%16,'tail_policy':'zero_pad_to_16','full_output':True})
            meta=json.loads(marker.read_text())
            for key in ['rhs','golden','ptr','cols','values']:
                assert meta['files_sha256'][key]==baseline_meta['files_sha256'][key],(source,n,key)
                assert digest(out/f'{key}.bin')==meta['files_sha256'][key]
            # Link the contemporaneous V0 input without changing the sealed baseline.
            link=out.parent/'V0'
            if not link.exists():link.symlink_to(os.path.relpath(base,link.parent),target_is_directory=True)
            print('V1_PREPARED',source.stem,n,flush=True)

    # Same implementation twice, distinguished by record index A/B. No new kernel.
    noise=dest/'null_control';noise.mkdir(exist_ok=True)
    null_tasks=[('SNAP_ca-HepTh',64),('SNAP_web-NotreDame',64),('Schmid_thermal1',256)]
    for name,n in null_tasks:
        for rep in range(3):
            key=f'null/{name}/N{n}/run{rep}'
            if key in state['completed']:continue
            out=noise/f'{name}_N{n}_run{rep}.json'
            run([str(exe),str(ROOT/'cases_v1'/name/f'N{n}'),'24','10','30',str(20261017+rep),str(out),'V0','V0'],out)
            state['completed'].append(key);state['last_completed']=key;save(status,state)
            print('V1_NULL_DONE',key,flush=True)

    jobs=[(rep,f.stem,n) for rep in range(3) for f in files for n in [16,64,256]]
    random.Random(20261017).shuffle(jobs)
    for rep,name,n in jobs:
        key=f'paired/{name}/N{n}/run{rep}'
        if key in state['completed']:continue
        out=dest/'measurements'/name/f'N{n}'/f'run{rep}.json';out.parent.mkdir(parents=True,exist_ok=True)
        data=run([str(exe),str(ROOT/'cases_v1'/name/f'N{n}'),'24','10','30',str(20261017+rep),str(out),'V0','V1'],out)
        assert [x['variant'] for x in data['records']]==['V0','V1']
        state['completed'].append(key);state['last_completed']=key;save(status,state)
        print('V1_PAIRED_DONE',sum(k.startswith('paired/') for k in state['completed']),'/72',key,flush=True)
    rows=[]
    for source in files:
        for n in [16,64,256]:
            x=[json.loads((dest/'measurements'/source.stem/f'N{n}'/f'run{rep}.json').read_text()) for rep in range(3)]
            v0=[statistics.median(y['records'][0]['samples_us']) for y in x]
            v1=[statistics.median(y['records'][1]['samples_us']) for y in x]
            paired=[statistics.median([a/b for a,b in zip(y['records'][0]['samples_us'],y['records'][1]['samples_us'])]) for y in x]
            rows.append({'matrix':source.stem,'n':n,'v0_process_medians_us':v0,'v1_process_medians_us':v1,
                         'v0_median_us':statistics.median(v0),'v1_median_us':statistics.median(v1),
                         'paired_speedup_per_process':paired,'paired_speedup':statistics.median(paired),
                         'v1_max_abs_error':max(y['records'][1]['max_abs_error'] for y in x)})
    save(dest/'summary.json',{'version':'V1','configurations':24,'paired_processes':72,'null_processes':9,'rows':rows,
                             'correctness':True,'stable_speedup_assessed':False,'stop_before':'V2'})
    state.update(state='complete',stop_required=True,next_version='V2');save(status,state)
    print('V1_COMPLETE_STOP_BEFORE_V2',flush=True)


if __name__=='__main__':main()
