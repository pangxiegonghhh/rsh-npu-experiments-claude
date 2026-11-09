import json,sys,time
from pathlib import Path
from native import BASE
from bounded_case import run_case
while not (BASE/'logs/stage3-run-complete.json').exists():time.sleep(30)
partials=[]
for p in sorted((BASE/'work/stage3-post-catalog').glob('*.json')):
 old=BASE/'work/post-e'/p.stem;cp=old/'last-completed-sweep.checkpoint.json';rec=json.loads((old/'record.json').read_text()) if (old/'record.json').exists() else {};done=BASE/'work/stage3-partial-post'/p.stem/'record.json'
 if cp.exists() and not rec.get('order_path') and not done.exists():partials.append(run_case([sys.executable,'-B','scripts/recover_partial_post.py',str(p)],'stage3-partial-'+p.stem))
checks=[]
for matrix in ['reddit','ogbn-products']:
 p=BASE/'work/stage3-independent'/matrix/'status.json'
 if not p.exists():checks.append(run_case([sys.executable,'-B','scripts/independent_stage3.py',matrix],'stage3-independent-'+matrix))
status=[]
for matrix in ['reddit','ogbn-products']:
 p=BASE/'work/stage3-independent'/matrix/'status.json';status.append(json.loads(p.read_text()) if p.exists() else dict(matrix=matrix,status='INCOMPLETE',error='independent check did not produce a final record'))
receipt=dict(partial_recoveries=partials,independent_commands=checks,independent=status)
if all(r['status']=='OK' and r.get('independent_orders',0)>=3 for r in status):
 import subprocess
 with (BASE/'logs/stage3-build.stdout').open('w') as o,(BASE/'logs/stage3-build.stderr').open('w') as e:r=subprocess.run([sys.executable,'-B','scripts/build_stage3.py'],cwd=BASE,stdout=o,stderr=e)
 receipt.update(build_exitcode=r.returncode);print('STAGE3_BUILD_EXIT',r.returncode,flush=True)
else:receipt['needs_final_audit']=True;print('STAGE3_INDEPENDENT_NEEDS_AUDIT',flush=True)
(BASE/'logs/stage3-finish-receipt.json').write_text(json.dumps(receipt,indent=2))
