from __future__ import annotations
import concurrent.futures,datetime,hashlib,json,os,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];REPO=BASE/'repo'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(item:tuple)->dict:
    name,rel,args,marker=item;cwd=BASE/'work/gates'/name;cwd.mkdir(parents=True,exist_ok=False);assert not list(cwd.iterdir())
    command=[sys.executable,'-B',str(REPO/rel),*args];record={'name':name,'argv':command,'cwd':str(cwd),'initial_directory_entries':[],
        'started_utc':now(),'source_sha256':hashlib.sha256((REPO/rel).read_bytes()).hexdigest()};start=time.perf_counter()
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'};env.pop('RQ2_HK',None)
    with (BASE/f'logs/{name}.stdout.log').open('w')as out,(BASE/f'logs/{name}.stderr.log').open('w')as err:
        proc=subprocess.Popen(command,cwd=cwd,stdout=out,stderr=err,env=env,start_new_session=True);record['pid']=proc.pid
        (BASE/f'logs/{name}.command.json').write_text(json.dumps(record,ensure_ascii=False,indent=2));code=proc.wait(timeout=7200)
    stdout=(BASE/f'logs/{name}.stdout.log').read_text();record.update(returncode=code,ended_utc=now(),elapsed_sec=time.perf_counter()-start,
        first_line=stdout.splitlines()[0]if stdout.splitlines()else'',passed=code==0 and marker in stdout)
    if name in ('t21-reference','t23-reference'):record['passed'] &= record['first_line']==marker
    (BASE/f'logs/{name}.command.json').write_text(json.dumps(record,ensure_ascii=False,indent=2));print(name,record['passed'],code,round(record['elapsed_sec'],3),flush=True)
    return record
def main():
    jobs=[('t21-reference','第一层工作区/T17-空白一试算脚本/reproduce_cora.py',[],'Table A self-check: OK'),
      ('t22-reference','第一层工作区/T17-空白二试算脚本/reproduce_cora_rq3.py',[],'RQ3 Table 1/2 self-check: OK'),
      ('t23-reference','第一层工作区/T23参考实现/reproduce_cora_t23.py',[],'T23 Cora self-check: OK'),
      ('t23-conditions-reference','第一层工作区/T23派发/conditions_ref.py',['--cora-selfcheck'],'T23 conditions self-check: OK')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:records=list(pool.map(run,jobs))
    for item in [('t23-toys','第一层工作区/T23参考实现/toy_tests.py',[],'passed'),
                 ('t23-independent-reference','第一层工作区/T23参考实现/verify/indep_t23.py',[str(REPO/'第一层实验结果/cora-pilot-20261104/neutron-matrices/cora.mtx'),str(BASE/'work/gates/t23-reference/out/orders_t23.json')],'T23 independent check: OK')]:
        if item[0]=='t23-toys':
            # Toy success is determined from the process return code and retained stdout.
            r=run(item);r['passed']=r['returncode']==0;(BASE/'logs/t23-toys.command.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));records.append(r)
        else:records.append(run(item))
    result={'passed':all(r['passed']for r in records),'gates':records};(BASE/'logs/reference-gates.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    assert result['passed'],'Reference gate failed; no campaign result reporting allowed'
    print('ALL_REFERENCE_GATES_OK',flush=True)
if __name__=='__main__':main()
