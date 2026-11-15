"""Verify and safely extract M11 evidence without running recovered binaries."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,tarfile

def sha256(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def main()->None:
 p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('--sha256',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 assert sha256(a.archive)==a.sha256,'archive hash mismatch'
 a.out.mkdir(parents=True,exist_ok=False)
 with tarfile.open(a.archive,'r:gz') as t:
  members=t.getmembers();names=set()
  for m in members:
   n=PurePosixPath(m.name);assert not n.is_absolute() and '..' not in n.parts and m.name not in names,m.name
   assert m.isfile(),f'refuse non-regular archive member: {m.name}'
   names.add(m.name)
  t.extractall(a.out,members=members,filter='data')
 manifest=json.loads((a.out/'EVIDENCE-SHA256.json').read_text());verified=[]
 for name,want in manifest.items():
  file=a.out/name;assert file.is_file() and not file.is_symlink(),name;got=sha256(file);assert got==want,(name,want,got);verified.append(name)
 result=dict(status='PASS',archive_sha256=a.sha256,verified_files=len(verified),archive_members=len(members),recovered_binaries_executed=False)
 (a.out/'LOCAL-RETURN-VERIFICATION.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
