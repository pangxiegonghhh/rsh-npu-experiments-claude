from __future__ import annotations
import concurrent.futures,datetime,json,os,platform,signal,subprocess,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
from align_context import BASE,OUT,OLD,PROTOCOL,dump,sha,assert_runtime
from check_align_gates import gate2,gate3
def now()->str:return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(matrix:str,mnc:int,stage:str)->dict:
    member='C6'if mnc==0 else'C6-M';key=f'c6__{matrix}__{member}__W16__{mnc}'
    spec=BASE/'work/specs'/(key+'.json');assert sha(spec)==sha(OLD/'work/specs'/spec.name)
    output=OUT/'checks/gate2-cora-runs'if stage=='gate2'else OUT
    folder=BASE/'logs/jobs'/stage;folder.mkdir(parents=True,exist_ok=True);command=folder/(key+'.command.json');assert not command.exists(),key
    argv=[sys.executable,'-B',str(BASE/'scripts/run_align_case.py'),str(spec),str(output)]
    sources=[BASE/'scripts'/name for name in ('run_align_case.py','align_context.py','campaign.py','c6.py','fast.py','metrics_fast.py','dstage_fast.py','kahypar-cut-v1.3.7.ini')]
    ref=Path('/Users/Zhuanz/.codex/visualizations/2026/11/05/01a1ac73-0f55-70c0-8e27-bb94bed5ad09/t21-rq2-20261106/repo/第一层工作区/T17-空白一试算脚本')
    sources +=[ref/name for name in ('rq2lib.py','methods.py')]
    binaries=[BASE/'work'/name for name in ('librq2-v8.dylib','libmetrics.dylib','libdstage-v2.dylib')]+[p for p in (BASE/'deps').rglob('*')if p.is_file()and p.suffix in ('.so','.dylib')]
    record={'case':key,'stage':stage,'spec':json.loads(spec.read_text()),'spec_sha256':sha(spec),'argv':argv,'cwd':str(BASE/'work'),
            'started_utc':now(),'timeout_sec':7200,'max_parallel_cases':2,'source_sha256':{str(p):sha(p)for p in sources},'binary_sha256':{str(p):sha(p)for p in binaries}}
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'}
    for name in ('RQ2_NATIVE_LIB','RQ2_D_LIB','RQ2_FORCE_SPARSE_OVERLAP'):env.pop(name,None)
    record['thread_environment']={k:env[k]for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')}
    started=time.perf_counter()
    with (folder/(key+'.stdout.log')).open('w')as stdout,(folder/(key+'.stderr.log')).open('w')as stderr:
        proc=subprocess.Popen(argv,cwd=BASE/'work',stdout=stdout,stderr=stderr,env=env,start_new_session=True)
        record['pid']=proc.pid;dump(command,record)
        try:record['returncode']=proc.wait(timeout=7200)
        except subprocess.TimeoutExpired:
            record['timed_out']=True;os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            record['returncode']=proc.returncode
    record.update(ended_utc=now(),elapsed_sec=time.perf_counter()-started);dump(command,record)
    print('CASE FINISHED',stage,key,record['returncode'],round(record['elapsed_sec'],3),flush=True);return record
def main()->None:
    assert_runtime();assert json.loads((BASE/'logs/package-application.json').read_text())['passed']
    assert json.loads((OUT/'checks/gate1-failed-model-replay.json').read_text())['passed']
    sys.path.insert(0,str(BASE/'deps'));import kahypar,numpy,scipy
    dump(BASE/'logs/environment.json',{'observed_utc':now(),'python':sys.version,'python_executable':sys.executable,'platform':platform.platform(),
         'machine':platform.machine(),'logical_cpu_count':os.cpu_count(),'numpy':numpy.__version__,'scipy':scipy.__version__,
         'kahypar_version':getattr(kahypar,'__version__','unknown'),'kahypar_module':kahypar.__file__,'kahypar_sha256':sha(Path(kahypar.__file__)),
         'configuration_sha256':sha(BASE/'scripts/kahypar-cut-v1.3.7.ini'),'seed':0,'epsilon':0.0,'W':16,'repair_cap':8,
         'environment_differences_from_T21':'Isolated runtime and redirected output paths only; pinned campaign, SDK, configuration and native binaries retained.'})
    print('GATE 2 START',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:records=list(pool.map(lambda m:run('cora',m,'gate2'),(0,4)))
    assert all(r['returncode']==0 for r in records),'Gate 2 execution failed; no main cases started'
    print('GATE 2',gate2(),flush=True)
    print('MAIN START',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:records=list(pool.map(lambda m:run('pattern1',m,'main'),(0,1,4,16)))
    dump(BASE/'logs/main-records.json',records)
    print('GATE 3',gate3(),flush=True)
    print('MAIN_FINISHED',flush=True)
if __name__=='__main__':main()
