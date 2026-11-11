"""Verify the owned 20 cases, not the global campaign; no global seal/marker."""
import csv,hashlib,json,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];os.chdir(ROOT);sys.path.insert(0,str(ROOT/'scripts'))
from bounded_case import run_case
from collect_stage3 import collect
from audit_results import audit
assignment=json.loads((ROOT/'assignment.json').read_text());expected={r['case_id'] for r in assignment['remote_cases']}
complete=json.loads((ROOT/'logs/stage3-remote-split-complete.json').read_text());assert set(complete['case_ids'])==expected and len(expected)==20
assert all((ROOT/'work/stage3-cases'/key/'record.json').exists() for key in expected)
command=run_case([sys.executable,'-B','scripts/independent_stage3.py','ogbn-products'],'stage3-independent-ogbn-products',env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','NUMBA_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
assert command['exitcode']==0
independent=json.loads((ROOT/'work/stage3-independent/ogbn-products/status.json').read_text());assert independent['status']=='OK' and independent['independent_orders']>=3
coverage=collect();assert coverage['planned_cases']==20 and coverage['attempted']==20 and coverage['all_attempted'] and coverage['result_rows']==488
invariants=audit(ROOT/'work/stage3-collected/results.csv')
result=dict(passed=True,split_id=assignment['split_id'],host_id=assignment['remote_host_id'],case_ids=sorted(expected),coverage=coverage,arithmetic_invariants=invariants,independent=independent,completed_at=time.time(),scope='20 owned cases and 488 conditions only; numeric INCOMPLETE/SKIPPED statuses are preserved; no global completion claim',return_instructions='Copy raw directories/logs/source/ELFs, retain absolute WSL paths in original records, checksum every file. If total order bytes exceed50MiB, formal result archive carries ledger only and transfer actual orders separately as a directory.')
(ROOT/'logs/remote-return-ready.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('REMOTE_20_CASES_RETURN_READY; preserve all failures and orders.')
