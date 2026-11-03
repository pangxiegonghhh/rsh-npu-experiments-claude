"""Seal H-V evidence, frozen routes, and all raw profiling artifacts."""
from pathlib import Path
import base64,hashlib,json,subprocess,time,zlib
ROOT=Path(__file__).resolve().parents[1]
def main()->None:
    dest=ROOT/'results/hv';state=json.loads((dest/'progress.json').read_text())
    if state['state']=='complete':
        env={'time':time.time()}
        for k,cmd in [('device',['npu-smi','info']),('remaining_processes',['pgrep','-af','run_hv.py|run_hv_grid.py|rsh_runner'])]:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=30);env[k]={'exit':r.returncode,'output':r.stdout+r.stderr}
        (dest/'final_environment.json').write_text(json.dumps(env,indent=2))
    files={}
    def add(p: Path,name: str|None=None)->None:
        b=p.read_bytes();e={'sha256':hashlib.sha256(b).hexdigest()}
        try:e['text']=b.decode('utf-8')
        except UnicodeDecodeError:e['base64_zlib']=base64.b64encode(zlib.compress(b)).decode()
        files[name or str(p.relative_to(ROOT))]=e
    for p in sorted(dest.rglob('*')):
        if p.is_file() and p.suffix!='.tmp':add(p)
    for folder in ['cases_hv','cases_hv_grid']:
        for p in sorted((ROOT/folder).rglob('metadata.json')):
            if p.parent.name=='H-V':add(p)
    for folder in ['npu','rsh','scripts']:
        for p in sorted((ROOT/folder).glob('*')):
            if p.is_file():add(p,f'results/hv/source_snapshot/{folder}/{p.name}')
    raw=json.dumps({'schema':'rsh910b-backup-hv','version':'hv','state':state['state'],'files':files},ensure_ascii=False).encode();(ROOT.parent/'hv-transfer.txt').write_bytes(raw)
    check={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'files':len(files),'state':state['state']};(ROOT.parent/'hv-check.txt').write_text(json.dumps(check));print(json.dumps(check),flush=True)
if __name__=='__main__':main()
