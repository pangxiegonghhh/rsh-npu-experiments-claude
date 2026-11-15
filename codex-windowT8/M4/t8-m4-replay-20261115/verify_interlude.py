"""Run replay correctness between complete timing blocks, then resume the driver."""
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

root=Path(__file__).resolve().parent
parent,child=map(int,sys.argv[1:3])
record=dict(driver_pid=parent,block_child_pid=child,start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
            purpose='replay correctness between timing blocks; no overlapping NPU experiments')
os.kill(parent,signal.SIGSTOP)
try:
    children=Path(f'/proc/{parent}/task/{parent}/children').read_text().split()
    assert len(children)<=1,'Unexpected child processes'
    child=int(children[0]) if children else None
    record['observed_child_pid']=child
    child_log=None
    if child:
        args=Path(f'/proc/{child}/cmdline').read_bytes().decode().split('\0')
        assert args[1]=='timeblock','Unexpected timing child'
        child_log=Path(args[2]).with_suffix('.log')
    deadline=time.monotonic()+1200
    while child and Path(f'/proc/{child}').exists():
        if Path(f'/proc/{child}/stat').read_text().split()[2]=='Z':break
        assert time.monotonic()<deadline,'Timing child did not finish'
        time.sleep(5)
    if child_log:assert 'M4_ALL_PASS 2592 mode=timeblock' in child_log.read_text(),'Timing block failed'
    record['device_interlude_start_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    for mode,count in [('first',8),('check',40)]:
        with (root/f'{mode}-v1.log').open('w') as log:
            rc=subprocess.run([str(root/'build/t8_micro'),mode,str(root/f'results-{mode}-v1')],cwd=root,
                              stdout=log,stderr=subprocess.STDOUT).returncode
        (root/f'{mode}-v1.rc').write_text(str(rc))
        record[mode+'_rc']=rc
        assert rc==0,f'Replay {mode} failed'
        assert f'REPLAY_ALL_PASS {count} mode={mode}' in (root/f'{mode}-v1.log').read_text()
        print('REPLAY_GATE_PASS',mode,count,flush=True)
    record['status']='PASS'
except BaseException as e:
    record['status']='FAIL';record['error']=str(e)
    raise
finally:
    record['end_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
    (root/'interlude-registration.json').write_text(json.dumps(record,indent=2))
    os.kill(parent,signal.SIGCONT)
    print('FORMAL_DRIVER_RESUMED',parent,flush=True)
