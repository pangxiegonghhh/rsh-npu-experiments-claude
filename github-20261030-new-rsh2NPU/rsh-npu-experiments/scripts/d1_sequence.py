"""Finish the authorized D1 phases serially; stop on any error, never D2."""
from pathlib import Path
import fcntl,json,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d1'
def main():
    lock=(D/'sequence.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    started=time.monotonic()
    while True:
        state=json.loads((D/'progress.json').read_text())
        if state['state']=='measurements_complete':break
        if state['state']=='failed':raise RuntimeError(state.get('error'))
        if time.monotonic()-started>7200:raise TimeoutError('D1 measurement wait, inspect controller before resuming')
        time.sleep(10)
    for script,args,log in [('run_d1.py',['--phase','profile'],'profile-controller.log'),('run_d1.py',['--phase','finish'],'finish-controller.log'),('analyze_d1.py',[],'analysis-controller.log'),('export_d1.py',[],'export-controller.log'),('audit_d1.py',['--full-inputs'],'audit-controller.log'),('export_d1.py',[],'export-controller.log')]:
        print('D1_SEQUENCE',script,args,flush=True)
        with (D/log).open('a') as f:
            p=subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=3600)
        if p.returncode:raise RuntimeError((script,args,p.returncode,log))
    print('D1_SEQUENCE_COMPLETE_RECOVER_VERIFY_AND_SHUTDOWN_REQUIRED',flush=True)
if __name__=='__main__':main()
