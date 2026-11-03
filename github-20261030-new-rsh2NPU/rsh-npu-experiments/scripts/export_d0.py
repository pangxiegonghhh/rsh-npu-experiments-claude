"""Seal D0 evidence, programs, reused objects and small inputs; no experiments."""
from pathlib import Path
import base64,hashlib,json,shutil,zlib
ROOT=Path(__file__).resolve().parents[1]
def main()->None:
    dest=ROOT/'results/d0';state=json.loads((dest/'progress.json').read_text());assert state['state']=='complete'
    build=json.loads((dest/'build.json').read_text());saved=dest/'build_objects';saved.mkdir(exist_ok=True)
    index={}
    for i,(name,h) in enumerate(build['reused_original_objects_sha256'].items()):
        p=ROOT/name;data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==h
        target=saved/(str(i)+'_'+p.name);target.write_bytes(data);index[name]={'saved':str(target.relative_to(ROOT)),'sha256':h}
    for name in ['CMakeFiles/rsh_runner.dir/flags.make','CMakeFiles/rsh_runner.dir/link.txt']:
        target=saved/Path(name).name;shutil.copy2(ROOT/'build_v4'/name,target)
    (saved/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    shutil.copy2(ROOT/'build_v4/rsh_runner',dest/'device_binary/rsh_runner_original')
    files={}
    def add(p:Path,name:str|None=None)->None:
        data=p.read_bytes();entry={'sha256':hashlib.sha256(data).hexdigest()}
        if len(data)>65536:entry['base64_zlib']=base64.b64encode(zlib.compress(data)).decode()
        else:
            try:entry['text']=data.decode()
            except UnicodeDecodeError:entry['base64_zlib']=base64.b64encode(zlib.compress(data)).decode()
        files[name or str(p.relative_to(ROOT))]=entry
    for p in sorted(dest.rglob('*')):
        if p.is_file() and p.suffix!='.tmp':add(p)
    for p in sorted((ROOT/'cases_d0').rglob('*')):
        if p.is_file():add(p)
    for name in ['scripts/prepare_d0.py','scripts/run_d0.py','scripts/analyze_d0.py','scripts/export_d0.py','diagnostics/d0/runner.cpp']:
        add(ROOT/name,'results/d0/source_snapshot/'+name)
    raw=json.dumps({'schema':'rsh910b-d0-backup-v1','state':state['state'],'files':files},ensure_ascii=False).encode()
    (ROOT.parent/'d0-transfer.txt').write_bytes(raw)
    check={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'files':len(files),'state':state['state']}
    (ROOT.parent/'d0-check.txt').write_text(json.dumps(check));print(json.dumps(check),flush=True)
if __name__=='__main__':main()
