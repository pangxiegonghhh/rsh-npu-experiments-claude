"""Verify D1 transport and every entry before import; preserve identical local files."""
from pathlib import Path
import argparse,base64,hashlib,json,zlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('bundle',type=Path);ap.add_argument('check',type=Path);a=ap.parse_args();raw=a.bundle.read_bytes();c=json.loads(a.check.read_text());assert len(raw)==c['bytes'] and hashlib.sha256(raw).hexdigest()==c['sha256'];x=json.loads(raw);assert len(x['files'])==c['files'];prepared=[]
    for name,e in x['files'].items():
        p=ROOT/name;assert p.resolve().is_relative_to(ROOT.resolve());b=e['text'].encode() if 'text' in e else zlib.decompress(base64.b64decode(e['base64_zlib']));assert hashlib.sha256(b).hexdigest()==e['sha256'],name
        if p.exists():assert p.read_bytes()==b,'Preserve differing local file: '+name
        else:prepared.append((p,b))
    for p,b in prepared:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
    print(json.dumps({'passed':True,**c,'new_files':len(prepared),'existing_identical_preserved':c['files']-len(prepared)}))
if __name__=='__main__':main()
