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
src=json.loads((root/'expected-source-sha256.json').read_text())
for file,want in src.items():assert hashlib.sha256((root/file).read_bytes()).hexdigest()==want,file
env=[run(['npu-smi','info'],'npu-smi'),run(['gcc','--version'],'gcc-version'),
     run(['/usr/local/python3.11.15/bin/python','--version'],'python-version'),
     run(['/usr/local/Ascend/cann-9.0.0/bin/bisheng','--version'],'bisheng-version'),
     run(['/data/e0-supplement-r1/resource_query'],'resources')]
acl=ctypes.CDLL('libascendcl.so')
assert acl.aclInit(None)==0
count=ctypes.c_uint32();rc0=acl.aclrtGetDeviceCount(ctypes.byref(count))
logic=ctypes.c_int32();rc1=acl.aclrtGetLogicDevIdByUserDevId(0,ctypes.byref(logic))
physical=ctypes.c_int32();rc2=acl.aclrtGetPhyDevIdByLogicDevId(logic,ctypes.byref(physical))
assert [rc0,rc1,rc2]==[0,0,0] and count.value==1
assert acl.aclFinalize()==0
save('device-map.json',{'count':count.value,'user':0,'logic':logic.value,'physical':physical.value,'rc':[rc0,rc1,rc2]})
save('environment.json',{'commands':env,'ASCEND_HOME_PATH':os.environ.get('ASCEND_HOME_PATH'),'at_unix':time.time()})
versions={}
for p in Path('/usr/local/Ascend/cann-9.0.0').rglob('version.info'):
    if p.is_file():versions[str(p)]=p.read_text(errors='replace')
save('sdk-versions.json',versions)
run(['/usr/local/python3.11.15/bin/python','scripts/e1_experiment.py','prepare',str(root)],'prepare')
assert hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()=='b9debf29eb4983a52185ccf33d1f0f96ac02a0a82cd46efc22186b934a216926'
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
