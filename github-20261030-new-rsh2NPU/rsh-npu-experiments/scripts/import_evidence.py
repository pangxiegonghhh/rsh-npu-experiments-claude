"""Verify independent bundle digest and every entry before restoring local evidence."""
from pathlib import Path
import argparse,base64,hashlib,json,zlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('bundle',type=Path);p.add_argument('check',type=Path);args=p.parse_args()
    raw=args.bundle.read_bytes();check=json.loads(args.check.read_text());assert hashlib.sha256(raw).hexdigest()==check['sha256'] and len(raw)==check['bytes']
    data=json.loads(raw);assert len(data['files'])==check['files'];prepared=[]
    for name,entry in data['files'].items():
        target=ROOT/name;assert target.resolve().is_relative_to(ROOT.resolve())
        b=entry['text'].encode() if 'text' in entry else zlib.decompress(base64.b64decode(entry['base64_zlib']))
        assert hashlib.sha256(b).hexdigest()==entry['sha256'],name;prepared.append((target,b))
    for target,b in prepared:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
    print(json.dumps({'passed':True,**check},ensure_ascii=False))
if __name__=='__main__':main()
