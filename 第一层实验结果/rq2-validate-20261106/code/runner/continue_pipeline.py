from __future__ import annotations
import json,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
while True:
    expected=BASE/'logs/p0-expected-specs.json';record=BASE/'logs/p0-records.json';valid=BASE/'logs/ls-validation.json'
    if expected.exists() and record.exists() and valid.exists():
        e=json.loads(expected.read_text());r=json.loads(record.read_text())
        if len(e)==len(r):
            assert all(x['returncode']==0 for x in r),r
            assert json.loads(valid.read_text())['passed']
            break
    time.sleep(5)
print('P0 complete; starting P1',flush=True)
for stage in ('p1','independent'):
    with (BASE/f'logs/{stage}-driver.stdout.log').open('w') as out,(BASE/f'logs/{stage}-driver.stderr.log').open('w') as err:
        p=subprocess.run([sys.executable,str(BASE/'scripts/run_stage.py'),stage],cwd=BASE/'work',stdout=out,stderr=err)
    if p.returncode:raise SystemExit(p.returncode)
    print(stage,'finished',flush=True)
print('P1 pipeline finished; P2 dependencies next',flush=True)
