from __future__ import annotations
import datetime,json,os,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'delivery/第一层实验结果/rq2-validate-20261106'
while 'STAGE FINISHED p0' not in (BASE/'logs/p0-supplement-driver.stdout.log').read_text():time.sleep(5)
# Normalize the protocol label of already-queued reconstructed-wiki specs without changing data.
folder=OUT/'checks/task-label-normalizations'
if folder.exists():
    for p in folder.glob('*.json'):
        d=json.loads(p.read_text());old=d['raw_spec']['key'];new=d['canonical_spec']['key']
        for suffix in ('.command.json','.stdout.log','.stderr.log'):
            source=BASE/'logs/jobs'/(old+suffix);dest=BASE/'logs/jobs'/(new+suffix)
            if source.exists():shutil.copy2(source,dest)
        command=BASE/'logs/jobs'/(new+'.command.json')
        if command.exists():
            record=json.loads(command.read_text());record['raw_spec']=record['spec'];record['spec']=d['canonical_spec'];record['label_normalization_evidence']=str(p);command.write_text(json.dumps(record,ensure_ascii=False,indent=2))
for stage in ('p0','metadata','p1','independent'):
    if stage=='p1':
        assert json.loads((BASE/'logs/ls-backend-v3-validation.json').read_text())['passed']
        assert (BASE/'work/librq2-v3.dylib').exists()
    print('Starting',stage,flush=True)
    command=[sys.executable,str(BASE/'scripts/prepare_metadata.py')] if stage=='metadata' else [sys.executable,str(BASE/'scripts/run_stage.py'),stage]
    with (BASE/f'logs/all-{stage}.stdout.log').open('w') as out,(BASE/f'logs/all-{stage}.stderr.log').open('w') as err:
        p=subprocess.run(command,cwd=BASE/'work',stdout=out,stderr=err,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    if p.returncode:raise SystemExit(p.returncode)
    print(stage,'finished',flush=True)
print('READY_FOR_P2',flush=True)
