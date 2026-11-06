from __future__ import annotations
import concurrent.futures, datetime, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
sys.dont_write_bytecode=True
from campaign import BASE,OUT,P0,acquisition,dump,slug

def run(spec: dict) -> dict:
    path=BASE/'work/specs'/(spec['key']+'.json');path.parent.mkdir(exist_ok=True);dump(path,spec)
    logs=BASE/'logs/jobs';logs.mkdir(exist_ok=True)
    cmd=[sys.executable,str(BASE/'scripts/campaign.py'),str(path)]
    record={'spec':spec,'argv':cmd,'cwd':str(BASE/'work'),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'timeout_sec':7200}
    hashes={}
    for source in list((BASE/'scripts').glob('*.py'))+list((BASE/'scripts').glob('*.cpp'))+list((BASE/'work').glob('*.dylib')):
        h=hashlib.sha256(source.read_bytes()).hexdigest();hashes[source.name]=h
        dest=BASE/'logs/code-snapshots'/h/source.name;dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.exists():shutil.copy2(source,dest)
    record['code_sha256']=hashes
    start=time.perf_counter()
    with (logs/(spec['key']+'.stdout.log')).open('w') as out,(logs/(spec['key']+'.stderr.log')).open('w') as err:
        process=subprocess.Popen(cmd,cwd=BASE/'work',stdout=out,stderr=err,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'},start_new_session=True)
        record['pid']=process.pid;dump(logs/(spec['key']+'.command.json'),record)
        try:record['returncode']=process.wait(timeout=7200)
        except subprocess.TimeoutExpired:
            import signal
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            record.update(returncode=process.returncode,timed_out=True)
    record.update(elapsed_sec=time.perf_counter()-start,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    dump(logs/(spec['key']+'.command.json'),record)
    print('DONE',spec['key'],record['returncode'],round(record['elapsed_sec'],2),flush=True)
    return record

def specs(stage: str) -> list[dict]:
    out=[]
    available=[m for m,d in acquisition().items() if d['status']=='OK']
    for matrix in available:
        if stage=='p0':
            for member in P0:out.append(dict(matrix=matrix,member=member,kind='p0',W=16))
        elif stage=='p1':
            for beta in (.5,2.,4.):out.append(dict(matrix=matrix,member=f'C9-beta{beta:g}',kind='member',W=16))
            out.append(dict(matrix=matrix,member='B-RCM-ref',kind='member',W=16))
            if matrix in ('cora','ogbn-arxiv','dawson5','wiki-RfA'):
                for W in (32,64,128):
                    for member in ('B0','rsh-α0','C9-Gorder','C10-BP'):out.append(dict(matrix=matrix,member=member,kind='w',W=W))
            for start in ('C9-Gorder','rsh-α0','rabbit-pilot'):
                for tau in (2,3):
                    for lam in (0.,.5,1.,2.):
                        for seed in ((0,1,2) if matrix in ('cora','ogbn-arxiv') else (0,)):
                            out.append(dict(matrix=matrix,member='P-LS',kind='ls',W=16,start=start,tau=tau,**{'lambda':lam,'seed':seed}))
                if matrix in ('cora','ogbn-arxiv'):
                    for lam in (0.,.5,1.,2.):out.append(dict(matrix=matrix,member='P-LS-full-control',kind='ls',W=16,start=start,tau=None,**{'lambda':lam,'seed':0}))
        elif stage=='independent':
            for W in (16,32,64,128):
                members=P0 if W==16 else ('B0','rsh-α0','C9-Gorder','C10-BP')
                if W!=16 and matrix not in ('cora','ogbn-arxiv','dawson5','wiki-RfA'):continue
                for member in members:
                    for rule in ('indep-first','indep-CBM'):out.append(dict(matrix=matrix,member=member,kind='independent',W=W,rule=rule))
        elif stage=='p2':out.append(dict(matrix=matrix,member='SlashBurn',kind='member',W=16))
        elif stage=='c6':
            for mnc in (0,1,4,16):out.append(dict(matrix=matrix,member='C6' if mnc==0 else 'C6-M',kind='c6',W=16,mnc=mnc))
    for spec in out:
        spec['key']='__'.join([stage,spec['matrix'],slug(spec['member']),f'W{spec["W"]}']+[str(spec[k]) for k in ('start','tau','lambda','seed','rule','mnc') if k in spec])
    return out

if __name__=='__main__':
    stage=sys.argv[1];jobs=specs(stage);dump(BASE/'logs'/(stage+'-expected-specs.json'),jobs)
    print('START',stage,'jobs',len(jobs),flush=True)
    records=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=1 if stage=='independent' else 2) as pool:
        for result in pool.map(run,jobs):
            records.append(result);dump(BASE/'logs'/(stage+'-records.json'),records)
    print('STAGE FINISHED',stage,flush=True)
