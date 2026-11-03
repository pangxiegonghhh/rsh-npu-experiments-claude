"""CPU-only exact D3 restore using saved layouts, case SHA and prior base cases."""
from pathlib import Path
import argparse,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d3 import sha,read
D=ROOT/'results/d3'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--layouts',action='store_true');a=ap.parse_args();restored=0
    for label,e in read(D/'build.json')['programs'].items():
        src=D/'device_binary'/Path(e['path']).name;assert sha(src)==e['sha256'];dst=ROOT/e['path'];dst.parent.mkdir(exist_ok=True)
        if dst.exists():assert sha(dst)==e['sha256']
        else:shutil.copy2(src,dst);dst.chmod(0o755)
    for name,e in read(D/'build_objects/index.json').items():
        src=ROOT/e['saved'];assert sha(src)==e['sha256'];dst=ROOT/name;dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():assert sha(dst)==e['sha256']
        else:shutil.copy2(src,dst)
    if a.layouts:
        need={}
        for name,h in read(D/'case_manifest.json')['files'].items():
            q=ROOT/name
            if q.exists():assert sha(q)==h
            elif name.endswith('.bin'):need.setdefault(h,[]).append(q)
            else:raise FileNotFoundError(name+' should be in compact backup metadata')
        # Hash only files of missing sizes cannot help when size absent; canonical roots sufficient.
        for folder in ['results/d3/plans','cases_v0','cases_v2','cases_d1','cases_d3_smoke_source']:
            for p in (ROOT/folder).rglob('*.bin'):
                if not need:break
                if not p.is_file():continue
                h=sha(p)
                if h in need:
                    for dst in need.pop(h):
                        dst.parent.mkdir(parents=True,exist_ok=True)
                        if dst.is_symlink():dst.unlink()
                        dst.symlink_to(p.resolve());restored+=1
            if not need:break
        assert not need,{'missing_hashes':list(need),'hint':'Restore canonical V0/V2 and physical D1 smoke inputs first; see 恢复环境.md.'}
    print({'runtime_restored':True,'case_links_created':restored,'device_execution':False})
if __name__=='__main__':main()
