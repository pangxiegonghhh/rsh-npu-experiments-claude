"""Restore saved D1 runtime and exact CPU layouts without running device work."""
from pathlib import Path
import argparse,hashlib,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));D=ROOT/'results/d1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--verify-only',action='store_true');ap.add_argument('--layouts',action='store_true');a=ap.parse_args();b=json.loads((D/'build.json').read_text())
    pairs=[('rsh_runner_formal','build_d0/rsh_runner_d0',b['formal_executable_sha256']),('rsh_runner_profile','build_d1/rsh_runner_profile',b['event_executable_sha256'])]
    if (D/'api_build.json').exists():
        api=json.loads((D/'api_build.json').read_text());pairs.append(('rsh_runner_api','build_d1/rsh_runner_api',api['executable_sha256']))
    for name,dst,h in pairs:
        p=D/'device_binary'/name;assert sha(p)==h
        if not a.verify_only:
            q=ROOT/dst;q.parent.mkdir(parents=True,exist_ok=True)
            if q.exists():assert sha(q)==h
            else:shutil.copy2(p,q)
            q.chmod(0o755)
    for name,e in json.loads((D/'build_objects/index.json').read_text()).items():
        p=ROOT/e['saved'];assert sha(p)==e['sha256']
        if not a.verify_only:
            q=ROOT/name;q.parent.mkdir(parents=True,exist_ok=True)
            if q.exists():assert sha(q)==e['sha256']
            else:shutil.copy2(p,q)
    if a.layouts:
        from scripts.prepare_d1 import cases
        from scripts.run_d1 import smoke,verify
        cases();smoke();verify(json.loads((D/'case_manifest.json').read_text()))
    print(json.dumps({'passed':True,'device_executed':False,'verify_only':a.verify_only,'layouts':a.layouts}))
if __name__=='__main__':main()
