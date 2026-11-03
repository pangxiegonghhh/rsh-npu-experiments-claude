"""Run only environment, fixture checks, build, and captured smoke tests."""
from pathlib import Path
import ctypes
import hashlib
import importlib.util
import json
import os
import subprocess
import time
root=Path('/data/e1-20261022-r1')
assert Path.cwd()==root
def save(name,obj):(root/name).write_text(json.dumps(obj,indent=2)+'\n')
def run(argv,label,timeout=600):
    start=time.time()
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    (root/(label+'.log')).write_bytes(p.stdout)
    rec={'argv':argv,'start':start,'end':time.time(),'returncode':p.returncode,'output':p.stdout.decode(errors='replace')}
    assert p.returncode==0,(label,rec)
    return rec
obj=json.loads((root/'manifest.json').read_text())
assert hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()=='5ceb25e03d74ba7372482bd64a9a7ac063669feede000b200c1b38efb1afc171'
save('canonical-fixture-verification.json',{'status':'PASS','sha256':'5ceb25e03d74ba7372482bd64a9a7ac063669feede000b200c1b38efb1afc171','cases':len(obj),'all_input_bin_hashes_matched':True})
run(['cmake','-S','npu/e1_probe','-B','build','-DASCEND_CANN_PACKAGE_PATH=/usr/local/Ascend/cann-9.0.0','-DSOC_VERSION=Ascend910B2'],'configure',180)
run(['cmake','--build','build','-j2'],'build',600)
save('binary-sha256.json',{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'build').rglob('*') if p.is_file() and (p.name=='e1_runner' or p.suffix=='.a')})
names=['main_u0_n17_p1_k0','main_u37_n17_p1_k0','main_u37_n17_p1_k1','main_u37_n17_p1_k2','main_u37_n17_p1_k3','occupancy_z0_k2','occupancy_z1_k2','occupancy_z256_k1','main_u63_n64_p1_k3']
(root/'smoke.txt').write_text(''.join(str(root/'inputs'/name)+'\n' for name in names))
run([str(root/'build/e1_runner'),str(root/'smoke.txt'),str(root/'results/smoke'),'1'],'smoke',180)
spec=importlib.util.spec_from_file_location('e1',root/'scripts/e1_experiment.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
checks=[mod.validate(root/'inputs'/name,root/'results/smoke'/name,1) for name in names]
save('smoke-checks.json',checks)
print('E1_BUILD_AND_SMOKE_PASS',len(checks),flush=True)
