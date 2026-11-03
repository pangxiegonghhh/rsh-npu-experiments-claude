"""Authorized D2 only; select on dev then conditionally evaluate, preserve phases."""
from pathlib import Path
import fcntl,subprocess,sys,traceback,json,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d2 import read,save
D=ROOT/'results/d2'
def main():
    lock=(D/'sequence.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    def run(script,args,name):
        print('D2_SEQUENCE',name,flush=True)
        with (D/(name+'-controller.log')).open('a') as f:p=subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=7200)
        assert p.returncode==0,(name,p.returncode)
    try:
        for phase in ['prepare','measure','profile']:run('run_d2.py',['--phase',phase,'--scope','dev'],'dev-'+phase)
        run('analyze_d2.py',['--scope','dev'],'dev-analysis')
        if read(D/'threshold_selection.json')['selected_thresholds']==[8,4]:
            for phase in ['prepare','measure','profile']:run('run_d2.py',['--phase',phase,'--scope','eval'],'eval-'+phase)
            run('analyze_d2.py',['--scope','eval'],'eval-analysis')
        run('run_d2.py',['--phase','finish'],'finish');run('export_d2.py',[],'export');print('D2_COMPLETE_RECOVER_VERIFY_AND_SHUTDOWN_REQUIRED',flush=True)
    except BaseException:
        save(D/'sequence_error.json',dict(error=traceback.format_exc(),time_unix=time.time()));raise
if __name__=='__main__':main()
