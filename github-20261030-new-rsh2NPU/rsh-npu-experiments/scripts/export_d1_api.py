"""Seal supplementary D1 API evidence without replacing the formal D1 bundle."""
from pathlib import Path
import base64,hashlib,json,zlib
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d1'
def main():
    state=json.loads((D/'api_progress.json').read_text());assert state['state']=='complete';files={}
    def add(p,name=None):
        b=p.read_bytes();e={'sha256':hashlib.sha256(b).hexdigest()}
        if len(b)>65536:e['base64_zlib']=base64.b64encode(zlib.compress(b)).decode()
        else:
            try:e['text']=b.decode()
            except UnicodeDecodeError:e['base64_zlib']=base64.b64encode(zlib.compress(b)).decode()
        files[name or str(p.relative_to(ROOT))]=e
    for p in sorted(D.glob('api*')):
        if p.is_file():add(p)
        elif p.is_dir():
            for q in sorted(p.rglob('*')):
                if q.is_file():add(q)
    add(D/'device_binary/rsh_runner_api')
    add(ROOT/'diagnostics/d1/api_runner.cpp')
    for name in ['scripts/prepare_d1_api.py','scripts/d1_api.py','scripts/export_d1_api.py','scripts/audit_d1_api.py','diagnostics/d1/api_runner.cpp']:add(ROOT/name,'results/d1/api_source_snapshot/'+name)
    b=json.dumps({'schema':'d1-api-recovery-v1','files':files,'state':'complete'},ensure_ascii=False).encode();(ROOT.parent/'d1-api-transfer.txt').write_bytes(b);c={'bytes':len(b),'files':len(files),'sha256':hashlib.sha256(b).hexdigest(),'state':'complete'};(ROOT.parent/'d1-api-check.txt').write_text(json.dumps(c));print(json.dumps(c))
if __name__=='__main__':main()
