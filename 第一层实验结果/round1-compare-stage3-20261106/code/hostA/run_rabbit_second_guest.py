import gzip,hashlib,json,os,resource,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
key,filename=sys.argv[1:];root=Path('/scratch/rabbit-runs');root.mkdir(exist_ok=True);start=time.time();record=dict(key=key,input_filename=filename,start=start,threads=1,author_ref='f93776e9c1e1d4a8962ee56bc7ff0091e6fe12dd',requested_seed=None,seed_api='author demo exposes no RNG seed; deterministic serial execution',status='INCOMPLETE',input_storage='new ext4 scratch virtualdisk; compressed and decoded inputs not stored in RAM-backed root');gz=root/(key+'.edges.gz');edge=root/(key+'.edges');mapping=root/(key+'.mapping');stderr=root/(key+'.stderr');cmd=['/root/rabbit/demo/reorder',str(edge)];record['command']=cmd
try:
 urllib.request.urlretrieve('http://10.0.2.2:18765/'+filename,gz);record['input_gz_sha256']=digest(gz)
 with gzip.open(gz,'rb') as f,edge.open('wb') as out:shutil.copyfileobj(f,out)
 record['input_prepare_seconds']=time.time()-start;record['decoded_input_bytes']=edge.stat().st_size;tm=time.time();env=os.environ.copy();env['OMP_NUM_THREADS']='1'
 with mapping.open('w') as out,stderr.open('w') as err:
  try:rc=subprocess.run(cmd,stdout=out,stderr=err,env=env,timeout=7200).returncode
  except subprocess.TimeoutExpired:rc=124
 record.update(exitcode=rc,coarse_seconds=time.time()-tm,status='OK' if rc==0 else 'INCOMPLETE',mapping_sha256=digest(mapping),mapping_bytes=mapping.stat().st_size,peak_mem_mb=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss/1024)
except Exception as e:record.update(error=str(e))
finally:
 for p in [gz,edge]:
  if p.exists():p.unlink()
record.update(end=time.time());(root/(key+'.record.json')).write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
