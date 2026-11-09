import json,subprocess,time,sys,hashlib,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];out=BASE/'work/rabbit-coarse';out.mkdir(exist_ok=True);ssh=['ssh','-p','22221','-i',str(BASE/'work/.private/linux_ed25519'),'-o','UserKnownHostsFile='+str(BASE/'work/.private/known_hosts'),'-o','StrictHostKeyChecking=yes','root@127.0.0.1']
bootstrap=subprocess.run(ssh+['curl -fsS http://10.0.2.2:18765/run_rabbit.py -o /root/run_rabbit.py'],capture_output=True,text=True);assert bootstrap.returncode==0,bootstrap.stderr
env=subprocess.run(ssh+['uname -a; c++ --version; sha256sum /root/rabbit/demo/reorder /root/rabbit/rabbit_order.hpp /root/rabbit/demo/reorder.cc /root/gperftools-2.16/.libs/libtcmalloc_minimal.a; apk info -v numactl musl libstdc++'],capture_output=True,text=True);(BASE/'logs/rabbit-linux-environment.stdout').write_text(env.stdout);(BASE/'logs/rabbit-linux-environment.stderr').write_text(env.stderr)
def run(m,mode,rep):
 key=f'{m}-{mode}-repeat{rep}';start=time.time();r=subprocess.run(ssh+[f'python3 /root/run_rabbit.py {key} {m}-{mode}.edges.gz'],capture_output=True,text=True,timeout=7300);(BASE/'logs'/('rabbit-'+key+'.stdout')).write_text(r.stdout);(BASE/'logs'/('rabbit-'+key+'.stderr')).write_text(r.stderr);assert r.returncode==0,r.stderr;record=json.loads(r.stdout.strip().splitlines()[-1]);record['requested_replica_label']=rep
 if record['status']=='OK':
  raw=subprocess.run(ssh+['cat /root/rabbit-runs/'+key+'.mapping'],capture_output=True,timeout=120);assert raw.returncode==0;assert hashlib.sha256(raw.stdout).hexdigest()==record['mapping_sha256'];p=out/(key+'.mapping');p.write_bytes(raw.stdout);record['runtime_path']=str(p)
 stderr=subprocess.run(ssh+['cat /root/rabbit-runs/'+key+'.stderr'],capture_output=True,text=True);(out/(key+'.stderr')).write_text(stderr.stdout);(out/(key+'.record.json')).write_text(json.dumps(record,indent=2));print(key,record['status'],round(time.time()-start,1),flush=True);return record
gate=[]
for mode in ['B','U']:
 a=run('cora',mode,0);b=run('cora',mode,1);assert a['status']==b['status']=='OK' and a['mapping_sha256']==b['mapping_sha256'];gate.append(dict(mode=mode,first=a['mapping_sha256'],second=b['mapping_sha256'],identical=True))
(BASE/'logs/rabbit-reproducibility-gate.json').write_text(json.dumps(dict(passed=True,checks=gate,threads=1,seed_api_unavailable=True),indent=2))
records=[]
for m in ['ogbn-arxiv','wiki-RfA','dawson5','olafu','pattern1','human_gene1']:
 for mode in ['B','U']:records.append(run(m,mode,0))
for m in ['cora','ogbn-arxiv']:
 for mode in ['B','U']:
  for rep in [1,2]:
   if m=='cora' and rep==1:continue
   records.append(run(m,mode,rep))
(BASE/'logs/rabbit-coarse-batch.json').write_text(json.dumps(records,indent=2))
