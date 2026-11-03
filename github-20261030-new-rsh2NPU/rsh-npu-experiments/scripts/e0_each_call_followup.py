"""Close E0's per-call integrated repeat coverage, retaining each raw output."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tarfile,time
p=Path.cwd();out=p/'each-call-followup';out.mkdir(exist_ok=True)
def sha(path: Path) -> str:return hashlib.sha256(path.read_bytes()).hexdigest()
checkpoint=json.loads((p/'manifest-checkpoint.json').read_text())
for name,value in {**checkpoint['source_sha256'],**checkpoint['binary_sha256']}.items():assert sha(p/name)==value,name
headers=json.loads((p/'sdk-header-hashes.json').read_text())
for name,value in headers.items():assert sha(Path(name))==value,name
commands=[];all_records=[]
for mode in ('normal','direct'):
 for rep in range(3):
  dest=out/f'{mode}-{rep}';dest.mkdir(exist_ok=True)
  argv=[str(p/'repeat-each'),str(p/'integrated-inputs'),str(dest)]
  env={**os.environ,'RSH_E0_DIRECT_A':'1' if mode=='direct' else '0'}
  proc=subprocess.Popen(argv,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  command={'mode':mode,'rep':rep,'argv':argv,'pid':proc.pid,'start_unix':time.time(),'RSH_E0_DIRECT_A':env['RSH_E0_DIRECT_A']};commands.append(command)
  (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  try:log,_=proc.communicate(timeout=120)
  except subprocess.TimeoutExpired:
   proc.kill();log,_=proc.communicate();(dest/'run.log').write_bytes(log);raise
  (dest/'run.log').write_bytes(log);command.update({'returncode':proc.returncode,'end_unix':time.time()})
  (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert proc.returncode==0,log
  trace=json.loads((dest/'trace.json').read_text());assert trace['call_count']==20 and trace['status']=='PASS'
  for item in trace['records']:
   i=item['iteration'];assert item['negative_a']==(i//2)%2 and item['negative_b']==i%2
   assert item['status']=='PASS' and item['max_abs_error']==0 and item['packed_checked'] and item['padding_checked'] and item['guards_checked']
   all_records.append({**item,'mode':mode,'process_index':rep})
  print(mode,rep,'PASS',len(trace['records']),'individually checked calls',flush=True)
assert len(all_records)==120
(out/'checks.json').write_text(json.dumps(all_records,indent=2)+'\n')
(out/'repeat_each.cpp').write_bytes((p/'npu/e0_probe/repeat_each.cpp').read_bytes())
(out/'runner_guarded.cpp').write_bytes((p/'npu/runner_guarded.cpp').read_bytes())
(out/'run_followup.py').write_bytes(Path(__file__).read_bytes())
(out/'build-command.txt').write_text('Exact compiler argv and working directory are in build-command.json (derived from the validated CMake link command).\n')
metadata={'status':'PASS','call_count':120,'processes':6,'cases':['M30_K70_N40','ADJACENT_U17_U37_N33'],'calls_per_case_per_process':10,'paths':['normal','direct'],'every_call_checked':True,'every_call_output_saved':True,'max_abs_error':0,'parent_source_and_binaries_unchanged':True,'sdk_headers_unchanged':True,'executable_sha256':sha(p/'repeat-each'),'kernel_library_sha256':sha(p/'integrated-final/lib/librsh_kernels.a'),'parent_archive_sha256':'4f209a7ea54481c46cd563af599a5708d57e3b0ce4fadf4167c03e666491622d','end_unix':time.time()}
(out/'summary.json').write_text(json.dumps(metadata,indent=2)+'\n')
files=[x for x in out.rglob('*') if x.is_file()]
(out/'file-hashes.json').write_text(json.dumps({str(x.relative_to(out)):sha(x) for x in sorted(files)},indent=2)+'\n')
files.append(out/'file-hashes.json')
archive=p/'e0-each-call-followup.tar.gz'
with tarfile.open(archive,'w:gz') as tf:
 for x in sorted(files):tf.add(x,arcname=str(x.relative_to(out)),recursive=False)
info={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),'file_count':len(files),'call_count':120,'status':'PASS'}
(p/'each-call-transfer-info.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info),flush=True)

