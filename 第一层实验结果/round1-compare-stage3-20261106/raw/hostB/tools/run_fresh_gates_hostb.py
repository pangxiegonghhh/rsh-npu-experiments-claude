"""Execute fresh WSL gates; create readiness only after all actual checks pass."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assignment=json.loads((ROOT/'assignment.json').read_text())
prep=json.loads((ROOT/'logs/remote-port-preparation.json').read_text())
assert prep['preparation_completed'] and prep['host_id']==assignment['remote_host_id']
assert not (ROOT/'logs/remote-readiness.json').exists()
env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','NUMBA_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'}
env.pop('RQ3_LAYOUT_LIB',None)
jobs=[
 ('reference_tables',['scripts/run_reference_gates.py'],'logs/reference-gates.json',False),
 (None,['scripts/generate_pure.py','--matrix','cora','--method','C4-U','--W','16','--seed','0'],'work/generated/cora__C4-U__W16__seed0.record.json',False),
 ('candidate_equivalence',['scripts/gate_candidates.py'],'logs/candidate-port-gate.json',False),
 ('candidate_equivalence',['scripts/gate_rect.py'],'logs/rect-port-gate.json',False),
 ('LS_full',['scripts/gate_ls_full.py'],'logs/ls-full-port-gate.json',False),
 ('layout_v7',['scripts/gate_layouts_v4.py'],'logs/layout-v4-port-gate.json','v4'),
 ('layout_v7',['scripts/gate_layouts.py'],'logs/layout-port-gate.json',True),
 ('layout_v7',['scripts/gate_layouts_v7.py'],'logs/layout-v7-port-gate.json',True),
 ('layout_v7',['scripts/gate_rq3_tables_v7.py'],'logs/rq3-native-table-v7-gate.json',True),
 ('independent_sorted',['scripts/gate_independent_sorted.py'],'logs/independent-sorted-port-gate.json',False),
 ('memory_guard_units',['tools/check_linux_memory.py'],'logs/remote-memory-unit-gate.json',False),
]
receipts=[]
for i,(category,args,result,layout_override) in enumerate(jobs):
    p=ROOT/result
    assert not p.exists(), ('fresh gate output already exists',result)
    actual_env=dict(env)
    if layout_override: actual_env['RQ3_LAYOUT_LIB']=str(ROOT/'work'/('liblayouts-v4.dylib' if layout_override=='v4' else 'liblayouts-v7.dylib'))
    command=[sys.executable,'-B',*args];started=time.time()
    with (ROOT/'logs'/f'remote-fresh-gate-{i}.stdout').open('w') as out,(ROOT/'logs'/f'remote-fresh-gate-{i}.stderr').open('w') as err:
        completed=subprocess.run(command,cwd=ROOT,env=actual_env,stdout=out,stderr=err,timeout=7200)
    record=dict(command=command,cwd=str(ROOT),NPY_DISABLE_CPU_FEATURES=actual_env.get('NPY_DISABLE_CPU_FEATURES'),started_at=started,ended_at=time.time(),returncode=completed.returncode,source_sha256=sha(ROOT/args[0]),RQ3_LAYOUT_LIB=actual_env.get('RQ3_LAYOUT_LIB'),scope='fresh remote Cora/unit gate, not a formal products case')
    (ROOT/'logs'/f'remote-fresh-gate-{i}.command.json').write_text(json.dumps(record,indent=2)+'\n')
    assert completed.returncode==0 and p.exists(),args
    r=json.loads(p.read_text())
    assert r.get('passed') is True if category else r.get('status')=='OK',result
    if category: receipts.append(dict(category=category,path=result,sha256=sha(p)))
    print('FRESH_GATE_OK',args[0],flush=True)
official=ROOT/'logs/t23-conditions-reference.command.json';r=json.loads(official.read_text());assert r['passed'] and r['returncode']==0
receipts.append(dict(category='official40',path=str(official.relative_to(ROOT)),sha256=sha(official)))
ready=dict(passed=True,fresh_remote_gates=True,host_id=assignment['remote_host_id'],split_id=assignment['split_id'],created_at=time.time(),gate_receipts=receipts,preparation_receipt_sha256=sha(ROOT/'logs/remote-port-preparation.json'),note='All gates executed on this host; no copied macOS PASS accepted. Additional source repairs require a fresh run and evidence.')
(ROOT/'logs/remote-readiness.json').write_text(json.dumps(ready,ensure_ascii=False,indent=2)+'\n')
print('REMOTE_READINESS_OK; only the 20 assigned products cases may now run.')
