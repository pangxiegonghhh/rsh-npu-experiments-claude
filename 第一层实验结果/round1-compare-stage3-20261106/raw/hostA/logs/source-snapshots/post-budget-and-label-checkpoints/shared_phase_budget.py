import json,os,threading,time
from pathlib import Path
def start_budget(coarse_seconds,method_started_at,prefix,limit=7200):
 prefix=Path(prefix);coarse=float(coarse_seconds);remaining=limit-coarse-(time.time()-method_started_at);config=dict(method_limit_seconds=limit,coarse_computation_seconds=coarse,local_started_at=method_started_at,local_seconds_remaining_at_activation=max(0,remaining),definition='inherited Rabbit coarse computation plus entire new local/renumber/candidate phase; queue excluded',activated_at=time.time());Path(str(prefix)+'.cost-budget.json').write_text(json.dumps(config,indent=2))
 def exceeded():
  event=dict(config,status='INCOMPLETE',reason='combined Rabbit coarse and new phase exceeded method time limit; no truncated candidate accepted',triggered_at=time.time(),local_elapsed_seconds=time.time()-method_started_at,total_computation_seconds=coarse+time.time()-method_started_at,exitcode=124);Path(str(prefix)+'.cost-budget-trigger.json').write_text(json.dumps(event,indent=2));os.write(2,(event['reason']+'\n').encode());os._exit(124)
 if remaining<=0:
  event=dict(config,status='INCOMPLETE',reason='inherited Rabbit coarse computation already exhausts method time budget',exitcode=124);Path(str(prefix)+'.cost-budget-trigger.json').write_text(json.dumps(event,indent=2));raise TimeoutError(event['reason'])
 timer=threading.Timer(remaining,exceeded);timer.daemon=True;timer.start();return timer
