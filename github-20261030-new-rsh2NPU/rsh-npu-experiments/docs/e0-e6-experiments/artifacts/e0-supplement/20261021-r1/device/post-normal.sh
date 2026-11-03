while kill -0 3080 2>/dev/null; do sleep 2; done
python - <<'PY'
import json
r=json.load(open('results/normal-all/checks.json'));assert len(r)==203 and all(x['status']=='PASS' for x in r),(len(r),r[-1])
PY
if [ $? -ne 0 ]; then exit 1; fi
build/e0_split inputs/control_K16_N16 results/split-normal normal 1 > split-normal.log 2>&1
build/e0_split inputs/control_K16_N16 results/split-direct direct 1 > split-direct.log 2>&1
python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0,'scripts');from e0_supplement import validate
for name,direct in [('split-normal',False),('split-direct',True)]:
 r=validate(Path('inputs/control_K16_N16'),Path('results')/name,direct);print(name,r['status']);assert r['status']=='PASS'
PY
python scripts/e0_supplement.py run inputs build results/direct-expanded --select S2 --mode direct > direct-expanded.log 2>&1
python - <<'PY'
import subprocess
from pathlib import Path
args=['integrated-build/rsh_guarded','integrated-inputs','1','1','1','20261021','results/integrated-normal/results.json']+[str(p.relative_to('integrated-inputs')) for p in sorted(Path('integrated-inputs').glob('*/V1'))]
Path('integrated-command.txt').write_text(repr(args));p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);Path('integrated-normal.log').write_bytes(p.stdout);print('INTEGRATED_NORMAL_RC',p.returncode)
args[6]='results/integrated-direct/results.json'
import os
p=subprocess.run(args,env={**os.environ,'RSH_E0_DIRECT_A':'1'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);Path('integrated-direct.log').write_bytes(p.stdout);print('INTEGRATED_DIRECT_RC',p.returncode)
PY
echo POST_DONE
