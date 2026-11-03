"""Export V2 evidence and saved permutations, without rerunning experiments."""
from pathlib import Path
import base64,hashlib,json,subprocess,time,zlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    dest=ROOT/'results/v2';state=json.loads((dest/'progress.json').read_text())
    if state['state']=='complete':
        env={'time':time.time()}
        for key,cmd in [('device',['npu-smi','info']),('remaining_processes',['pgrep','-af','run_v2.py|rsh_runner'])]:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=30);env[key]={'exit':r.returncode,'output':r.stdout+r.stderr}
        (dest/'final_environment.json').write_text(json.dumps(env,indent=2))
    files={}
    def add(p,name=None):
        b=p.read_bytes();entry={'sha256':hashlib.sha256(b).hexdigest()}
        if p.suffix=='.bin':entry['base64_zlib']=base64.b64encode(zlib.compress(b)).decode()
        else:entry['text']=b.decode()
        files[name or str(p.relative_to(ROOT))]=entry
    for p in sorted(dest.rglob('*')):
        if p.is_file() and p.suffix in ['.json','.log','.bin']:add(p)
    for p in sorted((ROOT/'cases_v2').rglob('metadata.json')):
        if p.parent.name=='V2':add(p)
    for folder in ['npu','rsh','scripts']:
        for p in sorted((ROOT/folder).glob('*')):
            if p.is_file():add(p,f'results/v2/source_snapshot/{folder}/{p.name}')
    raw=json.dumps({'schema':'rsh910b-backup-v2','version':'v2','state':state['state'],'files':files},ensure_ascii=False).encode()
    (ROOT.parent/'v2-transfer.txt').write_bytes(raw)
    check={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'files':len(files),'state':state['state']}
    (ROOT.parent/'v2-check.txt').write_text(json.dumps(check));print(json.dumps(check),flush=True)
if __name__=='__main__':main()
