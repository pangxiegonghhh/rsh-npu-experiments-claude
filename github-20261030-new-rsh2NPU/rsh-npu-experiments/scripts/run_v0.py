"""Run only V0 and persist a checkpoint after every successful process.

Launch from project root. Re-running verifies provenance and skips completed jobs.
This controller deliberately contains no transition to another main version.
"""
from pathlib import Path
import hashlib
import json
import random
import statistics
import subprocess
import sys
import time

import numpy as np
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rsh.planner import Matrix, layout
from rsh.prepare import export


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2))
    tmp.replace(path)


def main():
    dest = ROOT / 'results/v0'
    dest.mkdir(parents=True, exist_ok=True)
    files = sorted((ROOT / 'inputs').glob('*.npz'))
    assert len(files) == 8, f'Expected eight matrices, found {len(files)}'
    provenance = {'sources': {str(f.relative_to(ROOT)): digest(f) for f in
                  sorted((ROOT/'npu').glob('*')) if f.is_file()},
                  'executable_sha256': digest(ROOT/'build_v4/rsh_runner'),
                  'inputs': {f.name:digest(f) for f in files},
                  'controller_sha256':digest(Path(__file__)),
                  'protocol': {'version':'V0','widths':[16,64,256], 'aiv_blocks':48,
                               'warmups':10,'samples':30,'processes':3,
                               'b_seed':'20261017 + N', 'b_rotation':'B and -B',
                               'comparison':'standalone baseline; no cross-version pairing yet'}}
    manifest=dest/'manifest.json'
    if manifest.exists():
        assert json.loads(manifest.read_text()) == provenance, 'Provenance changed; use a fresh result directory'
    else:
        save(manifest,provenance)
    statusfile=dest/'progress.json'
    state=json.loads(statusfile.read_text()) if statusfile.exists() else {'version':'V0','state':'running','completed':[]}
    state['state']='running';save(statusfile,state)

    # Explicitly exercise small, padded and zero rows. No other variant executes.
    smoke=dest/'smoke';smoke.mkdir(exist_ok=True)
    for m in [7,16,17,32,65]:
        for n in [33,64]:
            for cores in [1,24]:
                out=smoke/f'M{m}_N{n}_C{cores}.json'
                if out.exists() and json.loads(out.read_text()).get('correctness'):continue
                cmd=[str(ROOT/'build_v4/rsh_runner'),str(ROOT/f'cases/smoke_M{m}/N{n}'),str(cores),'1','2','20261017',str(out),'V0']
                r=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
                out.with_suffix('.log').write_text(r.stdout+r.stderr)
                if r.returncode:raise RuntimeError(f'Smoke failed: {out.name}: {r.stdout+r.stderr}')
    print('SMOKE_V0_PASS 20/20',flush=True)

    for f in files:
        a=Matrix.load(str(f));order=np.arange(a.shape[0]);plan=layout(a,order,{'w':16,'tail':[]},'V0')
        ref=csr_matrix((a.val.astype(np.float64),a.col,a.ptr),shape=a.shape)
        for n in [16,64,256]:
            out=ROOT/'cases_v0'/f.stem/f'N{n}'/'V0'
            if (out/'metadata.json').exists():continue
            t=time.perf_counter();b=np.random.default_rng(20261017+n).uniform(-1,1,(a.shape[1],n)).astype(np.float16)
            golden=(ref@b.astype(np.float64)).astype(np.float32)
            export(a,plan,b,golden,out,{'matrix':f.stem,'input_sha256':digest(f),'n':n,'b_seed':20261017+n,'reference':'FP64 CSR multiply, cast FP32','value_policy':'stored reproducible signed FP16; real sparsity structure'})
            meta=json.loads((out/'metadata.json').read_text());meta['rhs_reference_export_seconds']=time.perf_counter()-t
            save(out/'metadata.json',meta)
            print('PREPARED',f.stem,n,flush=True)
    jobs=[(run,f.stem,n) for run in range(3) for f in files for n in [16,64,256]]
    random.Random(20261017).shuffle(jobs)
    for run,name,n in jobs:
        key=f'{name}/N{n}/run{run}'
        if key in state['completed']:continue
        out=dest/'measurements'/name/f'N{n}'/f'run{run}.json';out.parent.mkdir(parents=True,exist_ok=True)
        cmd=[str(ROOT/'build_v4/rsh_runner'),str(ROOT/'cases_v0'/name/f'N{n}'),'24','10','30',str(20261017+run),str(out),'V0']
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
        out.with_suffix('.log').write_text(r.stdout+r.stderr)
        if r.returncode:
            state.update(state='failed',failed=key,error=(r.stdout+r.stderr)[-3000:]);save(statusfile,state)
            raise RuntimeError(f'{key}: {r.stdout+r.stderr}')
        result=json.loads(out.read_text());assert result['correctness'] and len(result['records'])==1
        assert result['records'][0]['variant']=='V0'
        state['completed'].append(key);state['last_completed']=key;save(statusfile,state)
        print('V0_DONE',len(state['completed']),'/ 72',key,flush=True)
    rows=[]
    for f in files:
        for n in [16,64,256]:
            rs=[json.loads((dest/'measurements'/f.stem/f'N{n}'/f'run{run}.json').read_text())['records'][0] for run in range(3)]
            medians=[statistics.median(r['samples_us']) for r in rs]
            rows.append({'matrix':f.stem,'n':n,'m':rs[0]['m'],'k':rs[0]['k'],
                         'process_medians_us':medians,'median_us':statistics.median(medians),
                         'max_abs_error':max(r['max_abs_error'] for r in rs),
                         'samples':sum(len(r['samples_us']) for r in rs)})
    save(dest/'summary.json',{'version':'V0','configurations':24,'processes':72,'correctness':True,'rows':rows,
                             'timing':'resident synchronized full call, includes output zeroing, excludes host preparation/H2D',
                             'limitations':'Conservative CSR AIV baseline; not a claim of state-of-the-art AIV performance.'})
    state.update(state='complete',next_version='V1',stop_required=True);save(statusfile,state)
    print('V0_COMPLETE_STOP_BEFORE_V1',flush=True)


if __name__=='__main__':
    main()
