"""Authorized D3 only; select on dev then conditionally evaluate, preserve phases."""
from pathlib import Path
import fcntl,subprocess,sys,traceback,json,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d3 import read,save
D=ROOT/'results/d3'
def main():
    lock=(D/'sequence.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    def run(script,args,name):
        print('D3_SEQUENCE',name,flush=True)
        with (D/(name+'-controller.log')).open('a') as f:p=subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=10800)
        assert p.returncode==0,(name,p.returncode)
    try:
        for phase in ['prepare','measure','profile','finish']:run('run_d3.py',['--phase',phase],phase)
        run('analyze_d3.py',[],'analysis');run('audit_d3.py',['--full-inputs'],'audit');run('export_d3.py',[],'export');print('D3_COMPLETE_RECOVER_VERIFY_AND_SHUTDOWN_REQUIRED',flush=True)
    except BaseException:
        save(D/'sequence_error.json',dict(error=traceback.format_exc(),time_unix=time.time()));raise
if __name__=='__main__':main()
