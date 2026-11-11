import hashlib,json,os,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def run_case(command,label,env=None,method_limit=7200,queue_limit=86400):
 log=BASE/'logs'/label;log.parent.mkdir(exist_ok=True);launched=time.time();record=dict(command=command,launched_at=launched,method_limit_seconds=method_limit,queue_limit_seconds=queue_limit,status='RUNNING',source_sha256={str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'scripts').glob('*') if p.is_file() and p.suffix in ['.py','.cpp']})
 path=Path(str(log)+'.command.json');path.write_text(json.dumps(record,indent=2));effective=None
 with open(str(log)+'.stdout','w') as out,open(str(log)+'.stderr','w') as err:
  p=subprocess.Popen(command,cwd=BASE,env=env,stdout=out,stderr=err);record['pid']=p.pid
  while True:
   marker=BASE/'logs/cpu-slot-starts'/f'{p.pid}.json'
   if effective is None and marker.exists():
    try:r=json.loads(marker.read_text())
    except json.JSONDecodeError:r={}
    if r.get('queued_at',0)>=launched-1:effective=r['acquired_at'];record['cpu_slot']=r
   rc=p.poll()
   if rc is not None:record.update(exitcode=rc,status='FINISHED' if rc==0 else 'INCOMPLETE');break
   now=time.time();timed=effective is not None and now-effective>=method_limit;queue_timed=effective is None and now-launched>=queue_limit
   if timed or queue_timed:
    p.terminate()
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:p.kill();p.wait()
    record.update(exitcode=124,status='INCOMPLETE',reason='actual method timeout, queue excluded' if timed else 'CPU queue timeout before method start',partial_checkpoint_policy='retain last completed-sweep checkpoint; independently recompute before reporting partial numbers');break
   time.sleep(.5)
 record.update(ended_at=time.time(),method_started_at=effective,queue_seconds=(effective or time.time())-launched,actual_method_seconds=time.time()-effective if effective else None);path.write_text(json.dumps(record,indent=2));return record
