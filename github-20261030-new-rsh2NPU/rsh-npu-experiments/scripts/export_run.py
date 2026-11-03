"""Seal textual experiment evidence for an authenticated browser download."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument('--version',choices=['v1'],default='v1')
    args=parser.parse_args();dest=ROOT/'results'/args.version
    state=json.loads((dest/'progress.json').read_text())
    if state['state']=='complete':
        env={'time':time.time()}
        for key,cmd in [('device',['npu-smi','info']),('remaining_processes',['pgrep','-af','run_v1.py|rsh_runner'])]:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
            env[key]={'exit':r.returncode,'output':r.stdout+r.stderr}
        (dest/'final_environment.json').write_text(json.dumps(env,indent=2))
    files={}
    def add(path: Path,name: str | None=None) -> None:
        data=path.read_text(errors='replace')
        if path.suffix=='.json':
            try:json.loads(data)
            except ValueError:return
        files[name or str(path.relative_to(ROOT))]={'text':data,'sha256':hashlib.sha256(data.encode()).hexdigest()}
    for f in sorted(dest.rglob('*')):
        if f.is_file() and f.suffix in ['.json','.log']:add(f)
    for f in sorted((ROOT/'cases_v1').rglob('metadata.json')):
        if f.parent.name=='V1':add(f)
    for folder in ['npu','rsh','scripts']:
        for f in sorted((ROOT/folder).glob('*')):
            if f.is_file():add(f,f'results/v1/source_snapshot/{folder}/{f.name}')
    data=json.dumps({'schema':'rsh910b-backup-v1','version':args.version,'state':state['state'],'files':files},ensure_ascii=False)
    target=ROOT.parent/'v1-transfer.txt';target.write_text(data)
    check={'sha256':hashlib.sha256(data.encode()).hexdigest(),'bytes':len(data.encode()),'files':len(files),'state':state['state']}
    (ROOT.parent/'v1-check.txt').write_text(json.dumps(check))
    print(json.dumps(check),flush=True)


if __name__=='__main__':main()
