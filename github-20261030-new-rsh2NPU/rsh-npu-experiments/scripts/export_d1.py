"""Seal completed D1 evidence and exact executable/objects, no device work."""
from pathlib import Path
import base64,hashlib,json,shutil,zlib
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'results/d1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    state=json.loads((D/'progress.json').read_text());assert state['state']=='complete'
    build=json.loads((D/'build.json').read_text());index={};saved=D/'build_objects';saved.mkdir(exist_ok=True)
    for i,(name,h) in enumerate(build['reused_original_objects_sha256'].items()):
        p=ROOT/name;assert sha(p)==h;q=saved/(str(i)+'_'+p.name);shutil.copy2(p,q);index[name]={'saved':str(q.relative_to(ROOT)),'sha256':h}
    for name in ['CMakeFiles/rsh_runner.dir/flags.make','CMakeFiles/rsh_runner.dir/link.txt']:shutil.copy2(ROOT/'build_v4'/name,saved/Path(name).name)
    (saved/'index.json').write_text(json.dumps(index,indent=2)+'\n')
    files={}
    def add(p,name=None):
        data=p.read_bytes();e={'sha256':hashlib.sha256(data).hexdigest()}
        if len(data)>65536:e['base64_zlib']=base64.b64encode(zlib.compress(data)).decode()
        else:
            try:e['text']=data.decode()
            except UnicodeDecodeError:e['base64_zlib']=base64.b64encode(zlib.compress(data)).decode()
        files[name or str(p.relative_to(ROOT))]=e
    for p in sorted(D.rglob('*')):
        if p.is_file() and p.suffix!='.tmp':add(p)
    # Full small fixtures, resolved through links; formal inputs reproduce from frozen old cases.
    for root in (ROOT/'cases_d1').glob('smoke_*/N*'):
        for arg in ['V0','V2','V2-Z/V2','H-V','G-only/V2','ST-only/V0']:
            for p in sorted((root/arg).iterdir()):
                if p.is_file():add(p)
    for root in (ROOT/'cases_d1').glob('*/N*'):
        if root.parent.name.startswith('smoke_'):continue
        for arg in ['V2-Z/V2','G-only/V2','ST-only/V0']:
            for name in ['metadata.json','config.txt','cube_ptr.bin','rowmap.bin','srows.bin','valid.bin']:add(root/arg/name)
    for name in ['scripts/prepare_d1.py','scripts/run_d1.py','scripts/analyze_d1.py','scripts/audit_d1.py','scripts/export_d1.py','scripts/d1_sequence.py','scripts/restore_d1_runtime.py','diagnostics/d1/profile_runner.cpp']:add(ROOT/name,'results/d1/source_snapshot/'+name)
    raw=json.dumps({'schema':'d1-recovery-v1','files':files,'state':'complete'},ensure_ascii=False).encode();(ROOT.parent/'d1-transfer.txt').write_bytes(raw)
    check={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'files':len(files),'state':'complete'};(ROOT.parent/'d1-check.txt').write_text(json.dumps(check));print(json.dumps(check),flush=True)
if __name__=='__main__':main()
