set -e
cmake -S npu/e0_probe -B build-final -DASCEND_CANN_PACKAGE_PATH=/usr/local/Ascend/cann-9.0.0 -DSOC_VERSION=Ascend910B2 > configure-final.log 2>&1
cmake --build build-final -j4 > build-final.log 2>&1
cmake -S npu -B integrated-final -DASCEND_CANN_PACKAGE_PATH=/usr/local/Ascend/cann-9.0.0 -DSOC_VERSION=Ascend910B2 > integrated-configure-final.log 2>&1
cmake --build integrated-final -j4 > integrated-build-final.log 2>&1
python scripts/e0_supplement.py run inputs build-final results/normal-final > normal-final.log 2>&1
build-final/e0_split inputs/control_K16_N16 results/split-normal-final normal 1 > split-normal-final.log 2>&1
build-final/e0_split inputs/control_K16_N16 results/split-direct-final direct 1 > split-direct-final.log 2>&1
python scripts/e0_supplement.py run inputs build-final results/direct-expanded-final --select S2 --mode direct > direct-expanded-final.log 2>&1
python - <<'PY'
import subprocess,os
from pathlib import Path
args=['integrated-final/rsh_guarded','integrated-inputs','1','1','1','20261021','results/integrated-normal-final/results.json']+[str(x.relative_to('integrated-inputs')) for x in sorted(Path('integrated-inputs').glob('*/V1'))]
for direct in [False,True]:
 name='integrated-direct-final' if direct else 'integrated-normal-final';args[6]='results/'+name+'/results.json'
 env={**os.environ,'RSH_E0_DIRECT_A':'1' if direct else '0'}
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120);Path(name+'.log').write_bytes(p.stdout);assert p.returncode==0,p.stdout
PY
python scripts/e0_finish_final.py > finish-final.log 2>&1
echo FINAL_PASS
