import json,subprocess,sys,time,traceback
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
while True:
 p=subprocess.run([sys.executable,'-B','scripts/collect_t23_first.py'],cwd=BASE,capture_output=True,text=True)
 if p.returncode:
  (BASE/'logs/t23-first-readiness-error.txt').write_text(p.stdout+p.stderr);raise SystemExit(p.returncode)
 coverage=json.loads((BASE/'work/t23-first-collected/coverage.json').read_text());(BASE/'logs/t23-first-readiness.json').write_text(json.dumps(dict(time=time.time(),coverage=coverage),indent=2))
 if coverage['complete']:
  with (BASE/'logs/build-t23-first.stdout').open('w') as o,(BASE/'logs/build-t23-first.stderr').open('w') as e:r=subprocess.run([sys.executable,'-B','scripts/build_t23_first.py'],cwd=BASE,stdout=o,stderr=e)
  print('FIRST_DELIVERY_BUILD_EXIT',r.returncode,flush=True);raise SystemExit(r.returncode)
 print('T23_FIRST_PROGRESS',coverage['own_cases_complete'],coverage['post_cases_complete'],len(coverage['missing_diag']),flush=True)
 time.sleep(30)
