"""Restore exact clear-validation programs/objects and aliases without device work."""
from pathlib import Path
import argparse,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.prepare_d1b import read,sha,cases
D=ROOT/'results/d1b'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--verify-only',action='store_true');ap.add_argument('--layouts',action='store_true');a=ap.parse_args();b=read(D/'build.json');pairs=[]
    for e in b['executables'].values():pairs.append((D/'device_binary'/Path(e['path']).name,ROOT/e['path'],e['sha256'],True))
    for name,e in read(D/'build_objects/index.json').items():pairs.append((ROOT/e['saved'],ROOT/name,e['sha256'],False))
    for src,dst,h,exe in pairs:
        assert sha(src)==h
        if not a.verify_only:
            dst.parent.mkdir(parents=True,exist_ok=True)
            if dst.exists():assert sha(dst)==h
            else:shutil.copy2(src,dst)
            if exe:dst.chmod(dst.stat().st_mode|0o111)
    if a.layouts:
        cases()
        for p,h in read(D/'case_manifest.json')['files'].items():assert sha(ROOT/p)==h
    print({'passed':True,'files':len(pairs),'device_executed':False,'verify_only':a.verify_only,'layouts':a.layouts})
if __name__=='__main__':main()
