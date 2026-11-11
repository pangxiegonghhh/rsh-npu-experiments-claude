import argparse,hashlib,json,subprocess,time
from pathlib import Path
from native import BASE
from resource_slots import acquire
ap=argparse.ArgumentParser();ap.add_argument('--matrix',choices=['reddit','ogbn-products'],required=True);args=ap.parse_args();assert (BASE/'delivery/round1-compare-20261106.receipt.json').exists();slot=acquire();ssh=['ssh','-p','22221','-i',str(BASE/'work/.private/linux_ed25519'),'-o','UserKnownHostsFile='+str(BASE/'work/.private/known_hosts_second'),'-o','StrictHostKeyChecking=yes','root@127.0.0.1'];out=BASE/'work/rabbit-coarse';out.mkdir(exist_ok=True);inputs=json.loads((BASE/'logs/rabbit-second-inputs.json').read_text());records=[]
for mode in ['B','U']:
 key=f'{args.matrix}-{mode}-repeat0';p=out/(key+'.record.json')
 if p.exists():records.append(json.loads(p.read_text()));continue
 r=subprocess.run(ssh+['python3 /root/run_rabbit_second_guest.py '+key+' '+args.matrix+'-'+mode+'.edges.gz'],capture_output=True,text=True,timeout=7600);(BASE/'logs'/('rabbit-second-'+key+'.stdout')).write_text(r.stdout);(BASE/'logs'/('rabbit-second-'+key+'.stderr')).write_text(r.stderr)
 if r.returncode==0:
  record=json.loads(r.stdout.strip().splitlines()[-1]);expected=next(x for x in inputs if x['matrix']==args.matrix and x['mode']==mode);assert record.get('input_gz_sha256')==expected['sha256'];record.update(requested_replica_label=0,actual_seed=None,host_input_record=expected)
  raw=subprocess.run(ssh+['cat /scratch/rabbit-runs/'+key+'.mapping'],capture_output=True,timeout=120)
  if raw.returncode==0:
   target=out/(key+'.mapping');target.write_bytes(raw.stdout);assert hashlib.sha256(raw.stdout).hexdigest()==record['mapping_sha256'];record['runtime_path']=str(target)
  err=subprocess.run(ssh+['cat /scratch/rabbit-runs/'+key+'.stderr'],capture_output=True);(out/(key+'.stderr')).write_bytes(err.stdout)
 else:record=dict(status='INCOMPLETE',key=key,error='guest controller transport failed; no scientific retry',exitcode=r.returncode,stderr=r.stderr)
 p.write_text(json.dumps(record,indent=2));records.append(record);print(key,record['status'],record.get('coarse_seconds'),flush=True)
(BASE/'logs'/('rabbit-second-'+args.matrix+'-complete.json')).write_text(json.dumps(records,indent=2));kernel=subprocess.run(ssh+['dmesg'],capture_output=True);(BASE/'logs'/('linux-second-dmesg-after-'+args.matrix+'.stdout')).write_bytes(kernel.stdout)
