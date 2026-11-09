import json,subprocess,sys,time
from pathlib import Path
from native import BASE
from collect_t22 import collect
last=None
while True:
 counts={n:len(list((BASE/'work'/n).glob(pattern))) for n,pattern in [('order-jobs','*.record.json'),('extra-order-jobs','*.record.json'),('t22-evaluations','*/status.json'),('t22-new-evaluations','*/status.json')]}
 value=tuple(counts.values())
 if value!=last:print('T22_READY_COUNTS',counts,flush=True);last=value
 if counts['order-jobs']==315 and counts['extra-order-jobs']==76 and counts['t22-evaluations']==85 and counts['t22-new-evaluations']==340:break
 time.sleep(30)
cmd=[sys.executable,'-B','scripts/derive_t22.py']
with (BASE/'logs/t22-derived-final.stdout').open('w') as o,(BASE/'logs/t22-derived-final.stderr').open('w') as e:r=subprocess.run(cmd,cwd=BASE,stdout=o,stderr=e)
assert r.returncode==0
collect();cov=json.loads((BASE/'work/t22-collected/coverage.json').read_text());print('T22_FINAL_COVERAGE',cov,flush=True)
if cov['OK']==170 and cov['result_rows']==4012 and cov['pls_records']==182:
 with (BASE/'logs/t22-build.stdout').open('w') as o,(BASE/'logs/t22-build.stderr').open('w') as e:r=subprocess.run([sys.executable,'-B','scripts/build_t22.py'],cwd=BASE,stdout=o,stderr=e)
 assert r.returncode==0
 print('T22_ARCHIVE_READY',flush=True)
else:print('T22_NEEDS_FINAL_AUDIT',flush=True)
