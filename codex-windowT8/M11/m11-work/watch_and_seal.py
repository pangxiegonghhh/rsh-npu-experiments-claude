"""A scoped CPU-only status/export helper; never controls or stops other jobs."""
from pathlib import Path
import json,time,hashlib,tarfile,html,os
ROOT=Path(__file__).resolve().parent

def snapshot()->dict:
 groups={}
 for name in ['stage3-a0','stage2-a0','a-micro-a1','a-micro-a2']:
  p=ROOT/('results-'+name);accepted=sorted(p.glob('b*-accepted.json'));attempts=p/'attempt-registration.json'
  records=json.loads(attempts.read_text()) if attempts.exists() else []
  groups[name]=dict(accepted=len(accepted),attempts=len(records),invalid_attempts=sum(not x.get('valid',False) for x in records),last_elapsed_s=json.loads(accepted[-1].read_text())['elapsed_s'] if accepted else None)
 rc=ROOT/'formal.rc'
 return dict(updated_utc=time.strftime('%Y-%m-%d %H:%M:%S UTC',time.gmtime()),stages=groups,formal_returncode=rc.read_text().strip() if rc.exists() else None)

def publish(data:dict)->None:
 raw=json.dumps(data,indent=2);tmp=ROOT/'live-status.tmp';tmp.write_text(raw);tmp.replace(ROOT/'live-status.json')
 link='<p><a href="m11-evidence-complete.tar.gz" download>Download M11 complete evidence</a></p>' if (ROOT/'m11-evidence-complete.tar.gz').exists() else ''
 page='<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="30"><title>M11 experiment status</title></head><body><h1>M11 experiment status</h1><pre>'+html.escape(raw)+'</pre>'+link+'</body></html>'
 (ROOT/'live-status.html').write_text(page)

def seal()->None:
 paths=[p for p in ROOT.rglob('*') if p.is_file() and p.name not in ['m11-evidence-complete.tar.gz','archive-receipt.json','EVIDENCE-SHA256.json','live-status.json','live-status.html','live-status.tmp','watcher.log']]
 manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 stamp=ROOT/'EVIDENCE-SHA256.json';stamp.write_text(json.dumps(manifest,indent=2));paths.append(stamp)
 target=ROOT/'m11-evidence-complete.tar.gz'
 with tarfile.open(target,'w:gz') as t:
  for p in paths:t.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
 receipt=dict(status='SEALED',archive=target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),files=len(paths),formal_rc=(ROOT/'formal.rc').read_text().strip())
 (ROOT/'archive-receipt.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)

def main()->None:
 while True:
  data=snapshot();publish(data)
  if data['formal_returncode'] is not None:
   seal();data=snapshot();data['archive']=json.loads((ROOT/'archive-receipt.json').read_text());publish(data);return
  time.sleep(30)
if __name__=='__main__':main()
