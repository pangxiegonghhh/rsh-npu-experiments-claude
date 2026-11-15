"""Verify emitted ND2NZ primitive counts in eight bounded official model paths."""
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

root=Path(__file__).resolve().parent
sim=root/'sim-v5-src';sim.mkdir(exist_ok=True)
(sim/'kernel.cpp').write_text((root/'kernel.cpp').read_text())
s=(root/'host.cpp').read_text()
assert 'std::max(2u,(3*cc.x[3]+cc.x[2]/16-1)/(cc.x[2]/16))' in s
s=s.replace('std::max(2u,(3*cc.x[3]+cc.x[2]/16-1)/(cc.x[2]/16))','2u')
s=s.replace('b(check?64ull*1024*1024:','b(check?4ull*1024*1024:')
s=s.replace('b<=a||','').replace('ck(aclrtSetOpExecuteTimeOut(15));','')
(sim/'host.cpp').write_text(s)
(sim/'CMakeLists.txt').write_text((root.parent/'t8-m5/sim-src/CMakeLists.txt').read_text())
with (root/'model-v5-build.log').open('w') as log:
    subprocess.run(['cmake','-S',str(sim),'-B',str(root/'build-sim-v5')],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run(['cmake','--build',str(root/'build-sim-v5'),'-j2'],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
print('MODEL_BUILD_COMPLETE',flush=True)

parent=int(sys.argv[1]);os.kill(parent,signal.SIGSTOP);records=[]
registration=dict(parent_pid=parent,start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),scope='official model instruction evidence, not silicon retired counters; no model timings used')
try:
    children=Path(f'/proc/{parent}/task/{parent}/children').read_text().split();assert len(children)<=1
    child=int(children[0]) if children else None
    deadline=time.monotonic()+1200;child_log=None
    if child:
        args=Path(f'/proc/{child}/cmdline').read_bytes().decode().split('\0')
        if len(args)>2:child_log=Path(args[2]).with_suffix('.log')
    while child and Path(f'/proc/{child}').exists():
        if Path(f'/proc/{child}/stat').read_text().split()[2]=='Z':break
        assert time.monotonic()<deadline,'Timing child did not finish';time.sleep(5)
    if child_log:assert 'M4_ALL_PASS 2592 mode=timeblock' in child_log.read_text()
    names=[]
    for n in (16,256):
      for dtype in ('FP16','FP32'):
       for merge in ('split','merge'):names.append(f'core-u64-r16-n{n}-{dtype}-hot-gap2-{merge}-gmax')
    for index,name in enumerate(names):
        listing=root/f'model-v5-{index}.list';listing.write_text(name+'\n')
        output=root/f'model-v5-{index}';logpath=root/f'model-v5-{index}.log'
        cmd=['msprof','op','simulator','--soc-version=Ascend910B2',f'--output={output}','--launch-count=1','--timeout=2','--aic-metrics=PipeUtilization','--dump=on',str(root/'build-sim-v5/t8_micro'),'first',str(root/f'results-model-v5-{index}'),'0',str(listing)]
        with logpath.open('w') as log:rc=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT).returncode
        assert rc==0 and 'M4_ALL_PASS 1 mode=first' in logpath.read_text(errors='replace'),f'Model data/counter/guard gate failed: {name}'
        traces=list(output.glob('**/dump/core0.cubecore0.instr_popped_log.dump'));assert len(traces)==1
        trace=traces[0];count=trace.read_text(errors='replace').count('MOV_OUT_TO_L1_MULTI_ND2NZ')
        expected=8 if '-merge-' in name else 32
        assert count==expected,f'{name}: got {count}, expected {expected}'
        records.append(dict(case=name,expected_ND2NZ=expected,model_ND2NZ=count,trace=str(trace.relative_to(root)),trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest()))
        print('MODEL_PATH_PASS',index,name,count,flush=True)
    registration['status']='PASS'
except BaseException as e:
    registration['status']='FAIL';registration['error']=str(e);raise
finally:
    registration['end_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    registration['records']=records
    (root/'model-v5-verification.json').write_text(json.dumps(registration,indent=2))
    os.kill(parent,signal.SIGCONT);print('FORMAL_DRIVER_RESUMED',parent,flush=True)
