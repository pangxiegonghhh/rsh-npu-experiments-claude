"""Restore exact archived D0 programs/objects without running NPU work."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def main()->None:
    ap=argparse.ArgumentParser();ap.add_argument('--verify-only',action='store_true');args=ap.parse_args()
    d=ROOT/'results/d0';b=json.loads((d/'build.json').read_text());index=json.loads((d/'build_objects/index.json').read_text())
    pairs=[(d/'device_binary/rsh_runner_original',ROOT/'build_v4/rsh_runner',b['base_executable_sha256'],True),(d/'device_binary/rsh_runner_d0',ROOT/'build_d0/rsh_runner_d0',b['diagnostic_executable_sha256'],True)]
    pairs += [(ROOT/e['saved'],ROOT/name,e['sha256'],False) for name,e in index.items()]
    pairs += [(d/'build_objects'/name,ROOT/'build_v4/CMakeFiles/rsh_runner.dir'/name,digest(d/'build_objects'/name),False) for name in ['flags.make','link.txt']]
    for src,dst,h,executable in pairs:
        assert digest(src)==h,src
        if args.verify_only:continue
        if dst.exists():assert digest(dst)==h,('Refuse to overwrite different runtime',dst)
        else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        if executable:dst.chmod(dst.stat().st_mode|0o111)
        assert digest(dst)==h
    print(json.dumps({'passed':True,'files':len(pairs),'verified_only':args.verify_only,'device_execution':False}))
if __name__=='__main__':main()
