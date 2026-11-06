from __future__ import annotations
import datetime,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
pause=BASE/'work/pause-new-p1-for-memory-handover'
expected={r['spec']['key']:r['pid'] for r in [json.loads(p.read_text()) for p in (BASE/'logs/jobs').glob('p1*.command.json')] if 'returncode'not in r}
print('Waiting for current task-owned cases to finish:',expected,flush=True)
while True:
    active=[json.loads(p.read_text()) for p in (BASE/'logs/jobs').glob('p1*.command.json') if 'returncode'not in json.loads(p.read_text())]
    ready=[]
    for d in active:
        marker=BASE/'logs/p1-handover-waiters'/(d['spec']['key']+'.json')
        if marker.exists() and json.loads(marker.read_text())['pid']==d['pid']:ready.append(d)
    if len(active)==2 and len(ready)==2 and all(d['spec']['key'] not in expected for d in active):break
    time.sleep(5)
driver=None;archive=BASE/'logs/p1-v5-controller-handover';archive.mkdir(exist_ok=True)
for d in ready:
    pid=d['pid'];args=subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True);assert str(BASE/'scripts/campaign.py') in args
    parent=int(subprocess.check_output(['ps','-p',str(pid),'-o','ppid='],text=True));pargs=subprocess.check_output(['ps','-p',str(parent),'-o','command='],text=True);assert str(BASE/'scripts/run_stage.py') in pargs
    if driver is None:driver=parent
    assert driver==parent
os.kill(driver,signal.SIGSTOP)
for d in ready:
    key=d['spec']['key']
    for suffix in ('.command.json','.stdout.log','.stderr.log'):
        path=BASE/'logs/jobs'/(key+suffix)
        if path.exists():shutil.copy2(path,archive/path.name)
    os.killpg(d['pid'],signal.SIGTERM)
    d.update(returncode=-15,interrupted_for='Controller handover before input load or computation; exact same case queued under verified low-memory V5.',ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (BASE/'logs/jobs'/(key+'.command.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2))
os.kill(driver,signal.SIGTERM);os.kill(driver,signal.SIGCONT)
(archive/'handover.json').write_text(json.dumps({'prior_driver_pid':driver,'prior_running_cases_allowed_to_finish':expected,'unstarted_waiters':ready,'new_workers':4,'backend':'verified V5, no dense overlap matrix on arxiv; no completed cases rerun'},ensure_ascii=False,indent=2))
pause.unlink()
for stage,workers in [('p1','4'),('independent','1')]:
    with (BASE/f'logs/v5-{stage}.stdout.log').open('w') as out,(BASE/f'logs/v5-{stage}.stderr.log').open('w') as err:
        code=subprocess.run([sys.executable,str(BASE/'scripts/run_stage.py'),stage],cwd=BASE/'work',stdout=out,stderr=err,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','RQ2_WORKERS':workers}).returncode
    if code:raise SystemExit(code)
    print(stage,'finished',flush=True)
with (BASE/'logs/all-pipeline.stdout.log').open('a') as f:f.write('\nVerified V5 continuation finished.\nREADY_FOR_P2\n')
print('READY_FOR_P2',flush=True)
