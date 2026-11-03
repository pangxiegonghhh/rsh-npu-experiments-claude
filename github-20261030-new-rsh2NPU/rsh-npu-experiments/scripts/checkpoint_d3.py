"""D3 completed-job checkpoint, called between processes with no NPU benchmark running."""
from pathlib import Path
import base64,hashlib,json,zlib
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d3'
def main():
    state=json.loads((D/'progress.json').read_text());tag='formal'+str(len(state['completed']))+'-profile'+str(len(state['profile_completed']));p=D/'checkpoints'/tag/'progress.json';p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():p.write_text(json.dumps(state,indent=2)+'\n')
    files={}
    def add(p):
        b=p.read_bytes();files[str(p.relative_to(ROOT))]=dict(sha256=hashlib.sha256(b).hexdigest(),base64_zlib=base64.b64encode(zlib.compress(b)).decode())
    add(p)
    for name in ['protocol.json','case_manifest.json','build.json','manifest.json','zero_probe.json','zero_probe.log','preflight.json','environment_aarch64.json','preparation_aarch64.json']:
        p=D/name
        if p.exists():add(p)
    for folder in ['orders','plans','device_binary','build_objects','source_snapshot','smoke']:
        for p in sorted((D/folder).rglob('*')):
            if p.is_file() and '.pending-' not in p.name and not (folder=='plans' and p.suffix=='.bin'):add(p)
    for key,folder in [('completed','measurements'),('profile_completed','profile')]:
        for name in state[key]:
            p=D/folder/(name+'.json')
            for q in [p,p.with_suffix('.before.json'),p.with_suffix('.after.json'),p.with_suffix('.process.json'),p.with_suffix('.log')]:add(q)
    for name in json.loads((D/'case_manifest.json').read_text())['files']:
        if not name.endswith('.bin'):add(ROOT/name)
    b=json.dumps(dict(schema='d3-checkpoint-v1',files=files,counts={key:len(state[key]) for key in ['completed','profile_completed']})).encode();(ROOT.parent/'d3-checkpoint.txt').write_bytes(b);c=dict(sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),files=len(files));(ROOT.parent/'d3-checkpoint-check.txt').write_text(json.dumps(c));print(c,flush=True)
if __name__=='__main__':main()
