"""Run only the already authorized D1b phases sequentially; stop on error."""
from pathlib import Path
import fcntl,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1b import read
D=ROOT/'results/d1b'
def main():
    lock=(D/'sequence.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);assert read(D/'progress.json')['state']=='prepared'
    for script,args,name in [('run_d1b.py',['--phase','measure'],'measure'),('run_d1b.py',['--phase','profile'],'profile'),('run_d1b.py',['--phase','finish'],'finish'),('analyze_d1b.py',[],'analysis'),('export_d1b.py',[],'export'),('audit_d1b.py',['--full-inputs'],'audit'),('export_d1b.py',[],'export')]:
        print('D1b_SEQUENCE',script,args,flush=True)
        with (D/(name+'-controller.log')).open('a') as f:p=subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=3600)
        if p.returncode:raise RuntimeError((script,args,p.returncode,name))
    print('D1b_SEQUENCE_COMPLETE_RECOVER_VERIFY_AND_SHUTDOWN_REQUIRED',flush=True)
if __name__=='__main__':main()
