"""Linux unit/guard gate. The 64MiB child limit is a synthetic fixture only."""
import hashlib, json, os, platform, resource, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
assert platform.system()=='Linux'
os.chdir(ROOT)
raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
proc=next(int(line.split()[1]) for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('VmHWM:'))
assert abs(raw-proc)<8192, (raw,proc)
started=time.time()
code="import sys,time;sys.path.insert(0,'scripts');from memory_guard import ensure_limit;ensure_limit(64*2**20);a=bytearray(96*2**20);time.sleep(10)"
p=subprocess.run([sys.executable,'-B','-c',code],cwd=ROOT,capture_output=True,timeout=15)
assert p.returncode==137, p.returncode
files=[]
for path in (ROOT/'logs/memory-guards').glob('*.json'):
    r=json.loads(path.read_text())
    if r.get('triggered_at',0)>=started and r.get('limit_bytes')==64*2**20: files.append((path,r))
assert len(files)==1 and files[0][1]['peak_rss_bytes']>64*2**20
r=dict(passed=True,host_platform=platform.platform(),linux_raw_ru_maxrss_KiB=raw,proc_VmHWM_KiB=proc,reported_MiB=raw/1024,formal_default_limit_bytes=8*2**30,synthetic_fixture_limit_bytes=64*2**20,synthetic_child_exitcode=137,guard_record=str(files[0][0].relative_to(ROOT)),guard_record_sha256=hashlib.sha256(files[0][0].read_bytes()).hexdigest(),note='Synthetic guard fixture only; no formal matrix run and no formal limit reduced.')
(ROOT/'logs/remote-memory-unit-gate.json').write_text(json.dumps(r,indent=2)+'\n')
print('LINUX_RSS_UNITS_AND_NATIVE_GUARD_OK')
