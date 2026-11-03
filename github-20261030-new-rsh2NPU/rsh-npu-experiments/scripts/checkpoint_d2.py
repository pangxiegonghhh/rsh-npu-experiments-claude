"""Read-only device-work checkpoint: seal only completed jobs and immutable inputs."""
from pathlib import Path
import base64,hashlib,json,zlib,time
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d2'
def main():
    state=json.loads((D/'progress.json').read_text());files={};tag='eval'+str(len(state['eval_completed']))+'-profile'+str(len(state['eval_profile_completed']));p=D/'checkpoints'/tag/'progress.json';p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():p.write_text(json.dumps(state,indent=2)+'\n')
    def add(p):
        b=p.read_bytes();files[str(p.relative_to(ROOT))]={'sha256':hashlib.sha256(b).hexdigest(),'base64_zlib':base64.b64encode(zlib.compress(b)).decode()}
    add(p)
    for name in ['protocol.json','build.json','zero_probe.json','zero_probe.log','threshold_selection.json','dev_analysis.json','dev_manifest.json','eval_manifest.json','dev_case_manifest.json','eval_case_manifest.json','dev_preparation_aarch64.json','eval_preparation_aarch64.json','dev_preflight.json','eval_preflight.json']:
        p=D/name
        if p.is_file():add(p)
    for folder in ['plans','device_binary','build_objects','source_snapshot','smoke']:
        for p in sorted((D/folder).rglob('*')):
            if p.is_file() and '.pending-' not in p.name and not (folder=='plans' and p.suffix=='.bin'):add(p)
    for scope in ['dev','eval']:
        for event,key,folder in [(False,'_completed','measurements'),(True,'_profile_completed','profile')]:
            for name in state[scope+key]:
                p=D/scope/folder/(name+'.json')
                for q in [p,p.with_suffix('.before.json'),p.with_suffix('.after.json'),p.with_suffix('.process.json'),p.with_suffix('.log')]:assert q.is_file();add(q)
        mf=D/(scope+'_case_manifest.json')
        if mf.exists():
            for name in json.loads(mf.read_text())['files']:
                if not name.endswith('.bin'):add(ROOT/name)
    b=json.dumps(dict(schema='d2-running-checkpoint-v1',files=files,device_execution=False,completed_counts={k:len(v) for k,v in state.items() if isinstance(v,list)})).encode();(ROOT.parent/'d2-running-transfer.txt').write_bytes(b);check=dict(sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),files=len(files));(ROOT.parent/'d2-running-check.txt').write_text(json.dumps(check));print(check,flush=True)
if __name__=='__main__':main()
