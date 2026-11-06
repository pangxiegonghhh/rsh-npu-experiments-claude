from __future__ import annotations
import json,os,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
while 'READY_FOR_P2' not in (BASE/'logs/all-pipeline.stdout.log').read_text():time.sleep(5)
assert json.loads((BASE/'logs/c6-fixture-validation.json').read_text())['passed']
for stage in ('p2','c6','audit','finalize'):
    print('Starting',stage,flush=True)
    if stage in ('p2','c6'):cmd=[sys.executable,str(BASE/'scripts/run_stage.py'),stage]
    else:cmd=[sys.executable,str(BASE/'scripts/independent_audit.py' if stage=='audit' else BASE/'scripts/finalize.py')]
    with (BASE/f'logs/finish-{stage}.stdout.log').open('w') as out,(BASE/f'logs/finish-{stage}.stderr.log').open('w') as err:
        process=subprocess.run(cmd,cwd=BASE/'work',stdout=out,stderr=err,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    if process.returncode:raise SystemExit(process.returncode)
    print(stage,'finished',flush=True)
print('ARTIFACT_COMPLETE',flush=True)
